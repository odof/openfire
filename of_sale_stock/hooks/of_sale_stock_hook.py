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
                UPDATE  SALE_ORDER_LINE         SOL1
                SET     of_invoice_date_prev    = COALESCE(SUB1.min_date, SUB2.min_date)
                FROM    SALE_ORDER_LINE         SOL2
                LEFT JOIN
                        (   SELECT  PO.sale_line_id     AS line_id
                            ,       MIN(SP.min_date)    AS min_date
                            FROM    procurement_order   PO
                            JOIN    stock_move          SM
                                ON  SM.procurement_id   = PO.id
                            JOIN    stock_picking       SP
                                ON  SP.id               = SM.picking_id
                            WHERE   SP.state            NOT IN ('done', 'cancel')
                            GROUP BY
                                    PO.sale_line_id
                        )                       SUB1
                    ON  SUB1.line_id            = SOL2.id
                JOIN
                        (   SELECT  PO.sale_line_id     AS line_id
                            ,       MAX(SP.min_date)    AS min_date
                            FROM    procurement_order   PO
                            JOIN    stock_move          SM
                                ON  SM.procurement_id   = PO.id
                            JOIN    stock_picking       SP
                                ON  SP.id               = SM.picking_id
                            WHERE   SP.state            != 'cancel'
                            GROUP BY
                                    PO.sale_line_id
                        )                       SUB2
                    ON  SUB2.line_id            = SOL2.id
                WHERE   SOL1.of_invoice_policy  = 'ordered_delivery'
                AND     SOL2.id                 = SOL1.id
                """)
