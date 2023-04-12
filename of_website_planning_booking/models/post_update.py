# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFPlanningTache(models.Model):
    _inherit = 'of.planning.tache'

    @api.model
    def _update_version_10_0_1_1_0(self):
        """ Ajout des jours sur les taches déjà existantes """
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_website_planning_booking'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version < '10.0.1.1.0':
            self._cr.execute("""
            INSERT INTO of_planning_tache_jours_rel (tache_id, jour_id)
            SELECT      opt.id, oj.id
            FROM        of_planning_tache opt,
                        of_jours oj,
                        ir_model_data imd
            WHERE       oj.id = imd.res_id
            AND         imd.model = 'of.jours'
            AND         imd.module = 'of_utils'
            AND         imd.name IN ('of_jours_1', 'of_jours_2', 'of_jours_3', 'of_jours_4', 'of_jours_5')
            ON CONFLICT DO NOTHING
            """)
