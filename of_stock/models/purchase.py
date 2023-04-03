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
        self.filtered(lambda o: o.company_id.id in company_ids).generate_serial_number()
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

        # Pour chaque ligne avec suivi par numéro de série
        for line in self.mapped('order_line').filtered(lambda l: l.product_id.tracking == 'serial'):
            # On identifie quelle quantité n'a pas encore été traitée pour cet article et cette commande
            number = line.product_qty - production_lot_obj.search_count(
                [('name', 'ilike', line.order_id.name), ('product_id', '=', line.product_id.id)])

            # On crée autant de numéro de série que de quantité non traitée sur la ligne
            while number > 0:
                next_by_code = sequence_obj.next_by_code('stock.lot.serial')
                name = '%s %s %s' % (
                    line.order_id.name,
                    next_by_code,
                    line.order_id.partner_id and line.order_id.partner_id.name or '')
                ean13 = barcode_nomenclature_obj.sudo().sanitize_ean("%0.13s" % next_by_code)
                production_lot_obj.create({
                    'name': name,
                    'product_id': line.product_id.id,
                    'of_internal_serial_number': ean13,
                })
                number -= 1
