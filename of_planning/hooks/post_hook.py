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

    @api.model
    def _post_update_hook_v10_0_1_3_0(self):
        """ Deleting all old ir.rules """
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_planning')])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < "10.0.1.3.0"
        if actions_todo:
            env = self.env
            rules = [
                env.ref('of_planning.of_restrict_access_planning_team_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_planning_tasks_categ_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_planning_tasks_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_planning_reason_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_planning_tag_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_planning_template_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_hr_employee_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_planning_mail_templates_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_planning_sectors_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning.of_restrict_access_time_slots_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_planning_tournee.of_restrict_access_planning_search_template_time_slot_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_project_issue.of_restrict_access_planning_categ_sav_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_questionnaire.of_restrict_access_planning_survey_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_questionnaire.of_restrict_access_planning_survey_interv_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_questionnaire.of_restrict_access_planning_question_categ_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_questionnaire.of_restrict_access_planning_question_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_questionnaire.of_restrict_access_planning_question_response_sales_representative_rule',
                        raise_if_not_found=False),
                env.ref('of_service.of_restrict_access_planning_di_sales_representative_rule',
                        raise_if_not_found=False),
            ]
            for rule in rules:
                if rule:
                    rule.unlink()
