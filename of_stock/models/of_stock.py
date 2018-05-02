# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import float_utils

class Inventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"

    @api.multi
    def action_check(self):
        u"""
        Modification de la fonction définie dans le module stock
        Appel de _generate_moves() sur l'ensemble des lignes plutôt que sur les lignes 1 par 1
          permettra de gérer les doublons
        """
        for inventory in self:
            inventory.mapped('move_ids').unlink()
            inventory.line_ids._generate_moves()

class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    of_note = fields.Text(string="Notes")

    @api.model
    def create(self, values):
        # Retrait de la contrainte sur les lignes d'inventaire
        return super(InventoryLine, self.with_context(of_inventory_line_check_double=False)).create(values)

    @api.model
    def _of_get_groupby_params(self):
        return [
            'location_id',
            'prod_lot_id',
            'product_id',
            'partner_id',
            'package_id',
        ]

    def _generate_moves(self):
        moves = self.env['stock.move']
        Quant = self.env['stock.quant']

        # Modification OpenFire :
        # il faut regrouper les lignes d'inventaire par article, société, emplacement, lot, propriétaire, paquet
        grouped_lines = []
        grouped_lines_dict = {}
        params = self._of_get_groupby_params()
        # Le dernier paramètre est traité séparément, il ne contiendra pas un dictionnaire mais l'indice des lignes d'inventaire dans grouped_lines
        last_param = params.pop()
        for line in self:
            d = grouped_lines_dict
            for param in params:
                d = d.setdefault(line[param], {})
            if line[last_param] in d:
                # Note : l'opérateur |= ne rajoute pas les ids dans l'élément existant mais crée un nouvel élément.
                # De ce fait, on ne peut pas avoir l'objet line à la fois dans grouped_lines et grouped_lines_dict
                # car la synchronisation ne se ferait pas
                grouped_lines[d[line[last_param]]] |= line
            else:
                d[line[last_param]] = len(grouped_lines)
                grouped_lines.append(line)

        for lines in grouped_lines:
            line = lines[0]
            line._fixup_negative_quants()
            # Calcul de la quantité totale, avec possibilité d'udm différentes...
            product_qty = 0.0
            for l in lines:
                if l.product_uom_id == line.product_uom_id:
                    product_qty += l.product_qty
                else:
                    product_qty += l.product_uom_id._compute_quantity(l.product_qty, line.product_uom_id)
            theoretical_qty = l.product_uom_id._compute_quantity(line.theoretical_qty, line.product_uom_id)

            # Code copié depuis la fonction d'origine (module stock)
            if float_utils.float_compare(theoretical_qty, product_qty, precision_rounding=line.product_id.uom_id.rounding) == 0:
                continue
            diff = line.theoretical_qty - product_qty
            if diff < 0:  # found more than expected
                vals = line._get_move_values(abs(diff), line.product_id.property_stock_inventory.id, line.location_id.id)
            else:
                vals = line._get_move_values(abs(diff), line.location_id.id, line.product_id.property_stock_inventory.id)
            move = moves.create(vals)

            if diff > 0:
                domain = [('qty', '>', 0.0), ('package_id', '=', line.package_id.id), ('lot_id', '=', line.prod_lot_id.id), ('location_id', '=', line.location_id.id)]
                preferred_domain_list = [[('reservation_id', '=', False)], [('reservation_id.inventory_id', '!=', line.inventory_id.id)]]
                quants = Quant.quants_get_preferred_domain(move.product_qty, move, domain=domain, preferred_domain_list=preferred_domain_list)
                Quant.quants_reserve(quants, move)
            elif line.package_id:
                move.action_done()
                move.quant_ids.write({'package_id': line.package_id.id})
                quants = Quant.search([('qty', '<', 0.0), ('product_id', '=', move.product_id.id),
                                       ('location_id', '=', move.location_dest_id.id), ('package_id', '!=', False)], limit=1)
                if quants:
                    for quant in move.quant_ids:
                        if quant.location_id.id == move.location_dest_id.id:  # To avoid we take a quant that was reconcile already
                            quant._quant_reconcile_negative(move)
        return moves
