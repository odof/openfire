# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _update_version_10_0_2_2_0(self):
        """ Ajout des onglets Contrats + Interventions + Opportunités aux onglets des utilisateurs """
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_website_portal'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version < '10.0.2.2.0':
            self._cr.execute("""
            INSERT INTO res_users_of_tab_rel (user_id, tab_id)
            SELECT      ru.id, ot.id
            FROM        res_users ru,
                        of_tab ot,
                        ir_model_data imd
            WHERE       ot.id = imd.res_id
            AND         imd.model = 'of.tab'
            AND         imd.module = 'of_website_portal'
            AND         imd.name IN ('of_tab_intervention', 'of_tab_contract', 'of_tab_opportunity')
            ON CONFLICT DO NOTHING
            """)
