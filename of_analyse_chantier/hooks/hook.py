# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, SUPERUSER_ID


class OFAnalyseChantierHook(models.AbstractModel):
    _name ='of.analyse.chantier.hook'

    @api.model
    def _update_version_10_0_1_1_0_hook(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_analyse_chantier'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version and module_self.latest_version < '10.0.1.1.0':
            analyse_group = self.env.ref('of_analyse_chantier.of_group_analyse_chantier_user', raise_if_not_found=False)
            openfire_user = self.env['res.users'].search([('login', '=', 'openfire')])
            exempted_users = [SUPERUSER_ID, openfire_user.id]
            if analyse_group and any(uid not in exempted_users for uid in analyse_group.users._ids):
                self.env['ir.values'].set_default('sale.config.settings', 'of_create_analyse_auto', True)
