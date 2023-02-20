# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class OFSaleHook(models.AbstractModel):
    _name = 'of.sale.hook'

    def _init_group_of_can_modify_sale_price_unit(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_sale'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.3.3.0' or False
        if actions_todo:
            cr = self._cr
            # On ajoute les utilisateurs internes au groupe de modification de prix de vente
            cr.execute("""
                INSERT INTO res_groups_users_rel (gid, uid)
                SELECT  imd.res_id, rgur.uid
                FROM    res_groups_users_rel rgur,
                        ir_model_data imd
                WHERE   imd.model = 'res.groups'
                AND     imd.module = 'of_sale'
                AND     imd.name IN ('group_of_can_modify_sale_price_unit')
                AND     rgur.gid = (SELECT 	imd2.res_id
                                    FROM    ir_model_data imd2
                                    WHERE   imd2.model = 'res.groups'
                                    AND     imd2.module = 'base'
                                    AND     imd2.name IN ('group_user'));""")
