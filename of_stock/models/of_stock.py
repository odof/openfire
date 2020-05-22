# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import float_utils
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_inventory import Inventory
from odoo.addons.stock.models.stock_quant import Quant


@api.multi
def _get_inventory_lines_values(self):
    # TDE CLEANME: is sql really necessary ? I don't think so
    locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
    domain = ' location_id in %s'
    args = (tuple(locations.ids),)

    vals = []
    Product = self.env['product.product']
    # Empty recordset of products available in stock_quants
    quant_products = self.env['product.product']
    # Empty recordset of products to filter
    products_to_filter = self.env['product.product']

    # case 0: Filter on company
    if self.company_id:
        domain += ' AND company_id = %s'
        args += (self.company_id.id,)

    # case 1: Filter on One owner only or One product for a specific owner
    if self.partner_id:
        domain += ' AND owner_id = %s'
        args += (self.partner_id.id,)
    # case 2: Filter on One Lot/Serial Number
    if self.lot_id:
        domain += ' AND lot_id = %s'
        args += (self.lot_id.id,)
    # case 3: Filter on One product
    if self.product_id:
        domain += ' AND product_id = %s'
        args += (self.product_id.id,)
        products_to_filter |= self.product_id
    # case 4: Filter on A Pack
    if self.package_id:
        domain += ' AND package_id = %s'
        args += (self.package_id.id,)
    # case 5: Filter on One product category + Exahausted Products
    if self.category_id:
        categ_products = Product.search([('categ_id', '=', self.category_id.id)])
        domain += ' AND product_id = ANY (%s)'
        args += (categ_products.ids,)
        products_to_filter |= categ_products
    if hasattr(self, 'of_option') and self.of_option:
        domain += ' AND in_date <= %s'
        args += (self.date, )

    self.env.cr.execute("""SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
                FROM stock_quant
                WHERE %s
                GROUP BY product_id, location_id, lot_id, package_id, partner_id """ % domain, args)

    for product_data in self.env.cr.dictfetchall():
        # replace the None the dictionary by False, because falsy values are tested later on
        for void_field in [item[0] for item in product_data.items() if item[1] is None]:
            product_data[void_field] = False
        product_data['theoretical_qty'] = product_data['product_qty']
        if product_data['product_id']:
            product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
            quant_products |= Product.browse(product_data['product_id'])
        vals.append(product_data)
    if self.exhausted:
        exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
        vals.extend(exhausted_vals)
    return vals


@api.multi
def action_start(self):
    for inventory in self:
        vals = {'state': 'confirm'}
        if not self.of_option or not self.date:
            vals['date'] = fields.Datetime.now()
        if (inventory.filter != 'partial') and not inventory.line_ids:
            vals.update(
                    {'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()]})
        inventory.write(vals)
    return True


Inventory._get_inventory_lines_values = _get_inventory_lines_values
Inventory.prepare_inventory = action_start


@api.model
def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                            force_location_from=False, force_location_to=False):
    '''Create a quant in the destination location and create a negative
    quant in the source location if it's an internal location. '''
    force_date = self._context.get('inventory_date', False)
    price_unit = move.get_price_unit()
    location = force_location_to or move.location_dest_id
    rounding = move.product_id.uom_id.rounding
    vals = {
        'product_id': move.product_id.id,
        'location_id': location.id,
        'qty': float_round(qty, precision_rounding=rounding),
        'cost': price_unit,
        'history_ids': [(4, move.id)],
        'in_date': move.date if force_date else datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'company_id': move.company_id.id,
        'lot_id': lot_id,
        'owner_id': owner_id,
        'package_id': dest_package_id,
    }
    if move.location_id.usage == 'internal':
        # if we were trying to move something from an internal location and reach here (quant creation),
        # it means that a negative quant has to be created as well.
        negative_vals = vals.copy()
        negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
        negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
        negative_vals['cost'] = price_unit
        negative_vals['negative_move_id'] = move.id
        negative_vals['package_id'] = src_package_id
        negative_quant_id = self.sudo().create(negative_vals)
        vals.update({'propagated_from_id': negative_quant_id.id})

    picking_type = move.picking_id and move.picking_id.picking_type_id or False
    if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
        if qty != 1.0:
            raise UserError(_('You should only receive by the piece with the same serial number'))

    # create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
    return self.sudo().create(vals)


Quant._quant_create_from_move = _quant_create_from_move


class Inventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"

    date = fields.Datetime(readonly=False)
    of_option = fields.Boolean('Peut forcer la date', compute="_compute_of_option")

    @api.depends('company_id')
    def _compute_of_option(self):
        option = self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire')
        for inventory in self:
            inventory.of_option = option

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

    @api.multi
    def action_done(self):
        return super(Inventory, self.with_context(
                inventory_date=self.env['ir.values'].get_default(
                        'stock.config.settings', 'of_forcer_date_inventaire'))).action_done()


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    _order = "product_id, inventory_id, location_id, prod_lot_id"

    of_note = fields.Text(string="Notes")

    @api.multi
    def _write(self, vals):
        # Impossible de mettre à jour le référence/nom de l'article si présent
        # dans une ligne d'inventaire d'une autre société que la société courante de l'utilisateur.
        # Donc sudo pour bypasser les problèmes de droits.
        for key in vals.keys():
            if key not in ['product_name', 'product_code']:
                break
        else:
            self = self.sudo()
        return super(InventoryLine, self)._write(vals)

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
        option = self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire')
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

            optional_domain = []
            if option:
                optional_domain = [('in_date', '<=', line.inventory_id.date)]
            if diff > 0:
                domain = [('qty', '>', 0.0), ('package_id', '=', line.package_id.id), ('lot_id', '=', line.prod_lot_id.id), ('location_id', '=', line.location_id.id)]
                preferred_domain_list = [[('reservation_id', '=', False)], [('reservation_id.inventory_id', '!=', line.inventory_id.id)]]
                domain += optional_domain
                quants = Quant.quants_get_preferred_domain(move.product_qty, move, domain=domain, preferred_domain_list=preferred_domain_list)
                Quant.quants_reserve(quants, move)
            elif line.package_id:
                move.action_done()
                move.quant_ids.write({'package_id': line.package_id.id})
                quants = Quant.search([('qty', '<', 0.0), ('product_id', '=', move.product_id.id),
                                       ('location_id', '=', move.location_dest_id.id), ('package_id', '!=', False)] + optional_domain, limit=1)
                if quants:
                    for quant in move.quant_ids:
                        if quant.location_id.id == move.location_dest_id.id:  # To avoid we take a quant that was reconcile already
                            quant._quant_reconcile_negative(move)
        return moves

    def _get_quants(self):
        if self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire'):
            return self.env['stock.quant'].search([
                ('company_id', '=', self.company_id.id),
                ('location_id', '=', self.location_id.id),
                ('lot_id', '=', self.prod_lot_id.id),
                ('product_id', '=', self.product_id.id),
                ('owner_id', '=', self.partner_id.id),
                ('package_id', '=', self.package_id.id),
                ('in_date', '<=', self.inventory_id.date)])
        return super(InventoryLine, self)._get_quants()


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    of_forcer_date_inventaire = fields.Boolean(string='(OF) Date inventaire')

    @api.multi
    def set_of_forcer_date_inventaire_defaults(self):
        return self.env['ir.values'].sudo().set_default(
                'stock.config.settings', 'of_forcer_date_inventaire', self.of_forcer_date_inventaire)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def write(self, vals):
        if self._context.get('inventory_date') and 'date' in vals:
            vals.pop('date')
        return super(StockMove, self).write(vals)
