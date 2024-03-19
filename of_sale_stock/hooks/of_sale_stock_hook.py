# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class OFSaleStockHook(models.AbstractModel):
    _name = 'of.sale.stock.hook'

    def _create_fields_procurement_purchase(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_sale_stock'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.2.0.0' or False
        if actions_todo:
            cr = self._cr
            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % ('stock_move',
                                                                'of_procurement_purchase_line_id',
                                                                'int4'))
            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % ('stock_move', 'of_check', 'bool'))

    def _init_field_procurement_purchase(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_sale_stock'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.3.0.0' or False
        if actions_todo:
            cr = self._cr
            # compute les champs of_procurement_purchase_line_id et of_check
            cr.execute("""
                UPDATE stock_move AS sm
                SET of_procurement_purchase_line_id = po.purchase_line_id
                FROM procurement_order AS po
                WHERE po.move_dest_id = sm.id""")

            cr.execute("""
                UPDATE  stock_move                          SM1
                SET     of_check                            = TRUE
                FROM    stock_move                          SM2
                ,       stock_quant                         SQ
                ,       stock_quant_move_rel                SQMR
                WHERE   SM1.of_procurement_purchase_line_id IS NOT NULL
                AND     SM2.purchase_line_id                = SM1.of_procurement_purchase_line_id
                AND     SQ.reservation_id                   = SM1.id
                AND     SQMR.move_id                        = SM2.id
                ;""")

    @api.model
    def _post_v_10_0_3_1_0_hook(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_sale_stock'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < '10.0.3.1.0'
        if actions_todo:
            self.env.cr.execute("""
                UPDATE sale_order_line sol
                SET of_invoice_date_prev=sub.min_date
                FROM (SELECT po.sale_line_id line_id, sp.min_date min_date
                FROM procurement_order po
                JOIN stock_move sm ON sm.procurement_id=po.id
                JOIN stock_picking sp ON sp.id=sm.picking_id
                WHERE sp.state != 'cancel'
                GROUP BY po.sale_line_id, sp.min_date
                ORDER BY sp.min_date DESC) sub
                WHERE sol.of_invoice_policy = 'ordered_delivery'
                AND sub.line_id = sol.id"""
            )

