# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def button_approve(self):
        res = super(PurchaseOrder, self).button_approve()
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        orders_with_serial_management = self.filtered(lambda o: o.company_id.id in company_ids)
        orders_with_serial_management.generate_serial_number()
        orders_with_serial_management.preassign_serial_number()
        return res

    of_production_lot_ids = fields.One2many(
        comodel_name='stock.production.lot', string=u"Numéros de série", compute='_compute_of_production_lot_ids')
    of_production_lot_count = fields.Integer(
        string=u"Nombre de numéros de série", compute='_compute_of_production_lot_ids')
    of_display_production_lot = fields.Boolean(
        string=u"Afficher numéros de série dans les rapports", compute='_compute_of_production_lot_ids')

    @api.multi
    def _compute_of_production_lot_ids(self):
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        for order in self:
            order.of_production_lot_ids = order.mapped('order_line.of_production_lot_ids')
            order.of_production_lot_count = len(order.of_production_lot_ids)
            order.of_display_production_lot = order.of_production_lot_count and order.company_id.id in company_ids

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        self.of_transporter_id = self.picking_type_id.warehouse_id.partner_id.id

    @api.multi
    def action_view_production_lot(self):
        action = self.env.ref('stock.action_production_lot_form')
        result = action.read()[0]

        if len(self.of_production_lot_ids) > 1:
            result['domain'] = [('id', 'in', self.of_production_lot_ids._ids)]
        elif len(self.of_production_lot_ids) == 1:
            res = self.env.ref('stock.view_production_lot_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.of_production_lot_ids and self.of_production_lot_ids[0] or False
        return result

    @api.multi
    def button_generate_serial_number(self):
        self.ensure_one()
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        if self.company_id.id in company_ids:
            self.generate_serial_number()
        else:
            raise UserError(
                "La génération de numéro de série n'est pas disponible pour la société de cette commande fournisseur.")

    @api.multi
    def action_generate_serial_number(self):
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        orders_with_serial_management = self.filtered(lambda o: o.company_id.id in company_ids)
        orders_with_serial_management.generate_serial_number()

    @api.multi
    def action_preassign_serial_number(self):
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        orders_with_serial_management = self.filtered(
            lambda o: o.company_id.id in company_ids and o.state == 'purchase')
        orders_with_serial_management.preassign_serial_number()

    @api.multi
    def generate_serial_number(self):
        production_lot_obj = self.env['stock.production.lot']
        sequence_obj = self.env['ir.sequence']
        barcode_nomenclature_obj = self.env['barcode.nomenclature']

        # On parcourt les articles des commandes avec suivi par numéro de série
        for order in self:
            for product in order.mapped('order_line.product_id').filtered(lambda p: p.tracking == 'serial'):

                qty_todo = sum(order.order_line.filtered(lambda l: l.product_id.id == product.id).mapped('product_qty'))

                # On identifie quelle quantité a déjà été traitée pour cet article et cette commande
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
                    production_lot_obj.create({
                        'name': name,
                        'product_id': product.id,
                        'of_internal_serial_number': ean13,
                    })
                    number -= 1

    @api.multi
    def preassign_serial_number(self):
        production_lot_obj = self.env['stock.production.lot']
        operation_lot_obj = self.env['stock.pack.operation.lot']

        # On parcourt les articles des commandes avec suivi par numéro de série
        for order in self:
            for product in order.mapped('order_line.product_id').filtered(lambda p: p.tracking == 'serial'):
                # On récupère l'opération de réception liée à l'article en vue de l'attribution des lots.
                # Plusieurs lignes de commande avec un même article ne créées qu'une operation.
                pack_operation = order.mapped(
                    'order_line.move_ids.linked_move_operation_ids.operation_id').filtered(
                    lambda o: o.product_id.id == product.id)

                if pack_operation:
                    if len(pack_operation) > 1:
                        pack_operation = pack_operation[0]

                    # On recherche les numéros de série qui ont été générés pour cet article et cette commande
                    production_lots = production_lot_obj.search(
                        [('name', 'ilike', order.name), ('product_id', '=', product.id)])

                    for lot in production_lots:
                        # On vérifie que ce lot n'est pas déjà assigné à cette opération
                        if not operation_lot_obj.search(
                                [('lot_id', '=', lot.id), ('operation_id', '=', pack_operation.id)]):
                            # On attribue le lot à l'opération associée
                            operation_lot_obj.create({
                                'operation_id': pack_operation.id,
                                'qty': 0,
                                'qty_todo': 1,
                                'lot_id': lot.id,
                            })

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_production_lot_ids = fields.One2many(
        comodel_name='stock.production.lot', string=u"Numéros de série", compute='_compute_of_production_lot_ids')

    @api.multi
    def _compute_of_production_lot_ids(self):
        production_lot_obj = self.env['stock.production.lot']
        for line in self:
            line.of_production_lot_ids = production_lot_obj.search(
                [('name', 'ilike', line.order_id.name), ('product_id', '=', line.product_id.id)])
