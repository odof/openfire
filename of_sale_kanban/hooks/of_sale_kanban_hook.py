# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class OFSaleKanbanHook(models.AbstractModel):
    _name = 'of.sale.kanban.hook'

    def _init_group_of_can_modify_state_kanban(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_sale_kanban'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.1.1.0' or False
        if actions_todo:
            cr = self._cr
            # On ajoute les utilisateurs internes au groupe la modification d'étapes kanban du Devis / Bon de commande
            cr.execute("""
                INSERT INTO res_groups_users_rel (gid, uid)
                SELECT  imd.res_id, rgur.uid
                FROM    res_groups_users_rel rgur,
                        ir_model_data imd
                WHERE   imd.model = 'res.groups'
                AND     imd.module = 'of_sale_kanban'
                AND     imd.name IN ('sale_change_state_kanban')
                AND     rgur.gid = (SELECT   imd2.res_id
                                    FROM    ir_model_data imd2
                                    WHERE   imd2.model = 'res.groups'
                                    AND     imd2.module = 'base'
                                    AND     imd2.name IN ('group_user'));""")
