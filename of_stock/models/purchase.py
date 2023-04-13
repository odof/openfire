# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def button_confirm(self):
        super(PurchaseOrder, self).button_confirm()
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        order_with_serial_management = self.filtered(lambda o: o.company_id.id in company_ids)
        order_with_serial_management.generate_serial_number()
        return True

    @api.multi
    def action_generate_serial_number(self):
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        self.filtered(lambda o: o.company_id.id in company_ids).generate_serial_number()

    @api.multi
    def generate_serial_number(self):
        production_lot_obj = self.env['stock.production.lot']
        sequence_obj = self.env['ir.sequence']
        barcode_nomenclature_obj = self.env['barcode.nomenclature']
        operation_lot_obj = self.env['stock.pack.operation.lot']

        # Pour chaque ligne avec suivi par numéro de série
        for order in self:
            for product in order.mapped('order_line.product_id').filtered(lambda p: p.tracking == 'serial'):

                # On identifie quelle quantité a déjà été traitée pour cet article et cette commande
                qty_todo = sum(order.order_line.filtered(lambda l: l.product_id.id == product.id).mapped('product_qty'))

                # Il est possible d'avoir plusieurs lignes avec le même article,
                # donc on ne doit pas les prendre en compte
                qty_done = production_lot_obj.search_count(
                    [('name', 'ilike', order.name), ('product_id', '=', product.id)])

                number = qty_todo - qty_done

                # On crée autant de numéro de série que de quantité non traitée sur la ligne
                while number > 0:
                    next_by_code = sequence_obj.next_by_code('stock.lot.serial')
                    name = '%s %s %s' % (
                            order.name,
                            next_by_code,
                            order.partner_id and order.partner_id.name or '')
                    ean13 = barcode_nomenclature_obj.sudo().sanitize_ean("%0.13s" % next_by_code)
                    production_lot = production_lot_obj.create({
                        'name': name,
                        'product_id': product.id,
                        'of_internal_serial_number': ean13,
                    })
                    # Plusieurs lignes de commande avec un même article ne créées qu'une operation.
                    # On la récupère pour y ajouter le lot à faire.
                    pack_operation = order.mapped(
                        'order_line.move_ids.linked_move_operation_ids.operation_id').filtered(
                        lambda o: o.product_id.id == product.id)[0]
                    if pack_operation:
                        operation_lot_obj.create({
                            'operation_id': pack_operation.id,
                            'qty': 0,
                            'qty_todo': 1,
                            'lot_id': production_lot.id,
                        })
                    number -= 1
