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
                UPDATE sale_order_line sol
                SET of_invoice_date_prev=sub.min_date
                FROM (SELECT oskl.kit_id kit_id, sp.min_date min_date
                FROM of_saleorder_kit_line oskl
                JOIN procurement_order po on po.of_sale_comp_id=oskl.id
                JOIN stock_move sm ON sm.procurement_id=po.id
                JOIN stock_picking sp ON sp.id=sm.picking_id
                WHERE sp.state != 'cancel'
                GROUP BY oskl.kit_id, sp.min_date
                ORDER BY sp.min_date DESC) sub
                WHERE sol.of_invoice_policy = 'ordered_delivery'
                AND sub.kit_id = sol.kit_id
                AND sol.of_is_kit"""
            )
