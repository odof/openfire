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
        actions_todo = module_self and module_self.latest_version < '10.0.2.0.0' or False
        if actions_todo:
            cr = self._cr
            # compute les champs of_procurement_purchase_line_id et of_check
            cr.execute("""
                UPDATE stock_move AS sm
                SET of_procurement_purchase_line_id = (
                    SELECT purchase_line_id
                    FROM stock_move
                    WHERE move_dest_id = sm.id
                    LIMIT 1
                );""")

            cr.execute("""
                UPDATE stock_move AS sm
                SET of_check = TRUE
                WHERE id IN (
                    SELECT      sm1.id
                    FROM        stock_move as sm1
                    LEFT JOIN   stock_move sm2
                    ON          sm1.of_procurement_purchase_line_id = sm2.purchase_line_id
                    LEFT JOIN   stock_quant sq1
                    ON          sq1.reservation_id = sm1.id
                    LEFT JOIN   stock_quant_move_rel sqmr
                    ON          sqmr.move_id = sm2.id
                    WHERE       sm1.of_procurement_purchase_line_id is not null
                    AND         sm2.id is not null
                    AND         sq1.id is not null
                );""")
