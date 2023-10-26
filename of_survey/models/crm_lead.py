import logging

import werkzeug

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_survey = fields.Many2one('of.survey.survey', string='Survey')
    of_survey_user_input = fields.Many2one('of.survey.user_input', string="Survey User Input")
    of_survey_user_input_line = fields.One2many(
        'of.survey.user_input.line', related='of_survey_user_input.user_input_line_ids', string="Surver User Input Line"
    )
    of_question_ids = fields.One2many('of.survey.question', related='of_survey.question_ids', string='Questions')

    @api.onchange('of_survey')
    def _onchange_of_survey(self):
        if self.of_survey:
            # on va chercher s'il existe déjà un survey_user_input avec ce crm_lead
            # sinon, on le crée
            of_survey_user_input = self.env['of.survey.user_input'].search(
                [('of_crm_lead_id', '=', self._origin.id)], limit=1
            )
            if not of_survey_user_input:
                value = {
                    'survey_id': self.of_survey.id,
                    'of_crm_lead_id': self._origin.id,
                    'partner_id': self.env.user.partner_id.id,
                }
                of_survey_user_input = self.env['of.survey.user_input'].create(value)
            self.of_survey_user_input = of_survey_user_input

    def open_survey(self):
        url = '/of_survey/%s/%s' % (
            self.of_survey.access_token,
            self.of_survey_user_input.access_token,
        )
        return {
            'type': 'ir.actions.act_url',
            'name': "Start Survey",
            'target': 'self',
            'url': url,
        }
