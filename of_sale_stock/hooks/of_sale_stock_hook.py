# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


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
                SET of_procurement_purchase_line_id = (
                    SELECT purchase_line_id
                    FROM procurement_order
                    WHERE move_dest_id = sm.id
                    LIMIT 1
                )
                WHERE state NOT IN ('done', 'cancel');""")

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
