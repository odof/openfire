# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class OFKitSaleHook(models.AbstractModel):
    _name = 'of.kit.sale.hook'

    def _init_group_of_can_modify_pricing_kit(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_kit'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.1.2.0' or False
        if actions_todo:
            cr = self._cr
            # On ajoute les utilisateurs internes au groupe de modification de tarif et kit
            cr.execute("""
                INSERT INTO res_groups_users_rel (gid, uid)
                SELECT  imd.res_id, rgur.uid
                FROM    res_groups_users_rel rgur,
                        ir_model_data imd
                WHERE   imd.model = 'res.groups'
                AND     imd.module = 'of_kit'
                AND     imd.name IN ('sale_order_line_acess_pricing_kit')
                AND     rgur.gid = (SELECT 	imd2.res_id
                                    FROM    ir_model_data imd2
                                    WHERE   imd2.model = 'res.groups'
                                    AND     imd2.module = 'base'
                                    AND     imd2.name IN ('group_user'));""")

    @api.model
    def _post_v_10_0_1_3_0_hook(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_kit'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < '10.0.1.3.0'
        if actions_todo:
            self.env.cr.execute("""
                UPDATE  SALE_ORDER_LINE         SOL1
                SET     of_invoice_date_prev    = COALESCE(SUB1.min_date, SUB2.min_date)
                FROM    SALE_ORDER_LINE         SOL2
                LEFT JOIN
                        (   SELECT  OSKL.kit_id             AS kit_id
                            ,       MIN(SP.min_date)        AS min_date
                            FROM    of_saleorder_kit_line   OSKL
                            JOIN    procurement_order       PO
                                ON  PO.of_sale_comp_id      = OSKL.id
                            JOIN    stock_move              SM
                                ON  SM.procurement_id       = PO.id
                            JOIN    stock_picking           SP
                                ON  SP.id                   = SM.picking_id
                            WHERE   SP.state                NOT IN ('done', 'cancel')
                            GROUP BY
                                    OSKL.kit_id
                        )                       SUB1
                    ON  SUB1.kit_id             = SOL2.kit_id
                JOIN
                        (   SELECT  OSKL.kit_id             AS kit_id
                            ,       MAX(SP.min_date)        AS min_date
                            FROM    of_saleorder_kit_line   OSKL
                            JOIN    procurement_order       PO
                                ON  PO.of_sale_comp_id      = OSKL.id
                            JOIN    stock_move              SM
                                ON  SM.procurement_id       = PO.id
                            JOIN    stock_picking           SP
                                ON  SP.id                   = SM.picking_id
                            WHERE   SP.state                != 'cancel'
                            GROUP BY
                                    OSKL.kit_id
                        )                       SUB2
                    ON  SUB2.kit_id             = SOL2.kit_id
                WHERE   SOL1.of_invoice_policy  = 'ordered_delivery'
                AND     SOL2.id                 = SOL1.id
                AND     SOL1.of_is_kit          = True
                """)

    @api.model
    def _create_column_diff_comps_cost(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_kit'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < '10.0.1.3.1'
        if actions_todo:
            # On crée la colonne of_diff_cost_comps manuellement pour éviter le calcul sur toutes les lignes
            # existantes (trop long et inutile)
            self.env.cr.execute("ALTER TABLE sale_order_line ADD COLUMN of_diff_cost_comps bool;")
