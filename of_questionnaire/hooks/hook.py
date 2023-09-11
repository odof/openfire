# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, SUPERUSER_ID


class OFQuestionnaireHook(models.AbstractModel):
    _name ='of.questionnaire.hook'

    @api.model
    def _question_code_cleanup(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_questionnaire'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version:
            self.env.cr.execute("UPDATE of_questionnaire_line SET condition = 'f' WHERE condition_code IS NULL")
            self.env.cr.execute(
                "UPDATE of_planning_intervention_question SET condition = 'f' WHERE condition_code IS NULL")
            self.env.cr.execute(
                "UPDATE of_parc_installe_question SET condition = 'f' WHERE condition_code IS NULL")
