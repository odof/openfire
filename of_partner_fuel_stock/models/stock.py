# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_storage = fields.Boolean(string=u"Stockage et retrait à la demande des articles")

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self).do_transfer()
        for picking in self:
            if picking.of_storage:
                for line in picking.pack_operation_product_ids:
                    fuel_stock = self.sudo().env['of.res.partner.fuel.stock'].search(
                        [('partner_id', '=', picking.partner_id.id), ('product_id', '=', line.product_id.id)],
                        limit=1)
                    if fuel_stock:
                        fuel_stock.checkout_qty = fuel_stock.checkout_qty + line.qty_done

        return res
