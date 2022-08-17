# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_data_from_template(self, line, price, discount):
        values = super(SaleOrder, self)._get_data_from_template(line, price, discount)
        values.update({
            'of_storage': line.of_storage,
        })
        return values

    @api.multi
    def action_confirm(self):
        """
        Pour les commandes qui ont au moins une ligne marquée comme stockée et retirée à la demande :
            - On divise le BL
            - On incrémente le stock de combustible
        """
        res = super(SaleOrder, self).action_confirm()
        for order in self.filtered(lambda o: o.order_line.filtered(lambda l: l.of_storage)):
            # Division du BL
            for initial_picking in order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done']):
                order_lines = initial_picking.move_lines.mapped('procurement_id').mapped(lambda p: p.sale_line_id)
                kit_lines = initial_picking.move_lines.mapped('procurement_id').mapped(lambda p: p.of_sale_comp_id)
                storage_order_lines = order_lines.filtered(lambda l: l.of_storage)
                other_order_lines = order_lines.filtered(lambda l: not l.of_storage)
                storage_kit_lines = kit_lines.filtered(lambda l: l.of_storage and l.kit_id.order_line_id.of_storage)
                other_kit_lines = kit_lines.filtered(
                    lambda l: not l.of_storage or not l.kit_id.order_line_id.of_storage)
                if (storage_order_lines or storage_kit_lines) and (other_order_lines or other_kit_lines):
                    # On divise le BL en 2
                    storage_move_lines = storage_order_lines.mapped('procurement_ids').mapped('move_ids')
                    other_move_lines = other_order_lines.mapped('procurement_ids').mapped('move_ids')
                    storage_kit_move_lines = storage_kit_lines.mapped('procurement_ids').mapped('move_ids')
                    other_kit_move_lines = other_kit_lines.mapped('procurement_ids').mapped('move_ids')
                    # On copie le BL
                    new_picking = initial_picking.copy()
                    new_picking.of_storage = True
                    for line in (storage_move_lines + storage_kit_move_lines):
                        # On supprime la ligne du BL initial
                        line_to_delete = initial_picking.move_lines.filtered(
                            lambda l: l.procurement_id == line.procurement_id)
                        line_to_delete.action_cancel()
                        line_to_delete.unlink()
                    for line in (other_move_lines + other_kit_move_lines):
                        # On supprime la ligne du nouveau BL
                        line_to_delete = new_picking.move_lines.filtered(
                            lambda l: l.procurement_id == line.procurement_id)
                        line_to_delete.action_cancel()
                        line_to_delete.unlink()
                    initial_picking.action_assign()
                    new_picking.action_assign()
                elif storage_order_lines or storage_kit_lines:
                    initial_picking.of_storage = True

            # Stock de combustible
            product_info_list = []

            # On recherche tous les articles en stockage et retrait à la demande de la commande
            for order_line in order.order_line.filtered(lambda l: l.of_storage):
                if not order_line.of_is_kit:
                    product_info_list.append((order_line.product_id, order_line.product_uom_qty))
                else:
                    for kit_line in order_line.kit_id.kit_line_ids.filtered(lambda l: l.of_storage):
                        product_info_list.append(
                            (kit_line.product_id, kit_line.qty_per_kit * order_line.product_uom_qty))

            # On incrémente le stock de combustible pour ces articles (mise à jour ou création)
            for product, product_qty in product_info_list:
                fuel_stock = self.env['of.res.partner.fuel.stock'].\
                    search([('partner_id', '=', order.partner_id.id), ('product_id', '=', product.id)],
                           limit=1)
                if fuel_stock:
                    fuel_stock.ordered_qty = fuel_stock.ordered_qty + product_qty
                else:
                    self.env['of.res.partner.fuel.stock'].create({'partner_id': order.partner_id.id,
                                                                  'product_id': product.id,
                                                                  'ordered_qty': product_qty})
        return res

    @api.multi
    def action_cancel(self):
        # Gestion du stock de combustible
        for order in self:
            if order.state == 'sale' and order.order_line.filtered(lambda l: l.of_storage):

                product_info_list = []

                # On recherche tous les articles en stockage et retrait à la demande de la commande
                for order_line in order.order_line.filtered(lambda l: l.of_storage):
                    if not order_line.of_is_kit:
                        product_info_list.append((order_line.product_id, order_line.product_uom_qty))
                    else:
                        for kit_line in order_line.kit_id.kit_line_ids.filtered(lambda l: l.of_storage):
                            product_info_list.append(
                                (kit_line.product_id, kit_line.qty_per_kit * order_line.product_uom_qty))

                # On décrémente le stock de combustible pour ces articles
                for product, product_qty in product_info_list:
                    fuel_stock = self.env['of.res.partner.fuel.stock'].search(
                        [('partner_id', '=', order.partner_id.id), ('product_id', '=', product.id)],
                        limit=1)
                    if fuel_stock:
                        fuel_stock.ordered_qty = fuel_stock.ordered_qty - product_qty

        return super(SaleOrder, self).action_cancel()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_storage = fields.Boolean(string=u"Stockage et retrait à la demande des articles")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        self.of_storage = self.product_id.of_storage
        return res

    @api.onchange('of_storage')
    def onchange_of_storage(self):
        if self.of_is_kit:
            self.kit_id.kit_line_ids.write({'of_storage': self.of_storage, 'of_storage_readonly': not self.of_storage})


class OFSaleorderKitLine(models.Model):
    _inherit = 'of.saleorder.kit.line'

    of_storage = fields.Boolean(string=u"Stockage et retrait à la demande des articles")
    of_storage_readonly = fields.Boolean(string=u"Stockage et retrait à la demande en lecture seule")
