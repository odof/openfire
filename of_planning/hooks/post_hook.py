# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFPlanningInterventionHook(models.AbstractModel):
    _name = 'of.planning.intervention.hook'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        res = super(OFPlanningInterventionHook, self)._auto_init()
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_planning'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version < '10.0.1.2':
            # init M2M picking_manual_ids relation based on picking_id field
            cr.execute("""INSERT INTO of_planning_intervention_picking_manual_rel(intervention_id, picking_id)
SELECT id, picking_id
FROM of_planning_intervention
WHERE picking_id IS NOT NULL""")
        return res
