# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class OFPurchaseHook(models.AbstractModel):
    _name = 'of.purchase.hook'

    def _init_field_procurement_purchase(self):
        print('_init_field_procurement_purchase : %s' % self)
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_purchase'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.2.0.0' or False
        if actions_todo:
            print('actions_todo : %s' % actions_todo)
            cr = self._cr
            # compute les champs of_procurement_purchase_line_id et of_check
            cr.execute("""
                UPDATE stock_move AS sm
                SET of_procurement_purchase_line_id = (
                    SELECT id
                    FROM purchase_order_line
                    WHERE order_id IN (
                        SELECT id
                        FROM purchase_order
                        WHERE sale_order_id = (
                            SELECT id
                            FROM sale_order
                            WHERE name = (
                                SELECT name
                                FROM procurement_group
                                WHERE id = sm.group_id
                            )
                            AND partner_id = sm.partner_id
                        )
                    )
                    LIMIT 1
                );""")
            cr.execute("""
                UPDATE stock_move AS sm
                SET of_check = ANY(  
                    SELECT id 
                    FROM stock_quant
                    WHERE id IN sm.reserved_quant_ids
                    AND id IN (
                        SELECT quant_ids
                        FROM purchase_order
                        WHERE purchase_line_id IS NOT NULL
                        AND purchase_line_id = sm.of_procurement_purchase_line_id
                    )
                )
                WHERE of_procurement_purchase_line_id IS NOT NULL;""")
        print('FIN : %s' % actions_todo)
