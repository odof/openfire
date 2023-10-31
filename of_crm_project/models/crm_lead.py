# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_template_id = fields.Many2one(comodel_name='of.crm.project.template', string="Project")
    of_project_line_ids = fields.One2many(comodel_name='of.crm.project.line', inverse_name='lead_id', string="Entries")
    of_date_project = fields.Date(string="Project date")

    # Linked Partner fields
    of_interlocutor = fields.Many2one(comodel_name='res.partner', string="Interlocutor")
    of_decision_maker = fields.Many2one(comodel_name='res.partner', string="Decision maker")
    of_architect = fields.Many2one(comodel_name='res.partner', string="Architect")
    of_labor_force = fields.Many2one(comodel_name='res.partner', string="Labor force")
    of_prime_contractor = fields.Many2one(comodel_name='res.partner', string="Prime contractor")
    of_engineering_office = fields.Many2one(comodel_name='res.partner', string="Engineering office")

    of_survey = fields.Many2one(comodel_name='of.survey.survey', string="Survey")
    of_survey_user_input = fields.Many2one(comodel_name='of.survey.user_input', string="Survey User Input")
    of_survey_user_input_line = fields.One2many(
        comodel_name='of.survey.user_input.line',
        related='of_survey_user_input.user_input_line_ids',
        string="Surver User Input Line",
    )
    of_question_ids = fields.One2many(
        comodel_name='of.survey.question', related='of_survey.question_ids', string="Questions"
    )

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
            self.of_survey_user_input.write({'state': 'new'})

    def open_survey(self):
        url = f'/of_survey/{self.of_survey.access_token}/{self.of_survey_user_input.access_token}'
        return {
            'type': 'ir.actions.act_url',
            'name': _("Start Survey"),
            'target': 'self',
            'url': url,
        }

    @api.onchange('of_template_id')
    def _onchange_of_template_id(self):
        for lead in self:
            if lead.of_template_id:
                lead.update({'of_project_line_ids': [Command.clear()]})
                attr_vals = {}
                vals = []
                for attr in lead.of_template_id.attr_ids:
                    attr_vals['attr_id'] = attr.id
                    attr_vals['type'] = attr.type
                    attr_vals['name'] = attr.name
                    attr_vals['sequence'] = attr.sequence
                    if attr.type == 'char':
                        attr_vals['val_char'] = attr.val_char_default
                    elif attr.type == 'text':
                        attr_vals['val_text'] = attr.val_text_default
                    elif attr.type == 'selection':
                        attr_vals['val_select_id'] = attr.val_select_id_default
                    else:
                        attr_vals['val_bool'] = attr.val_bool_default
                    vals.append(Command.create(attr_vals.copy()))
                lead.update({'of_project_line_ids': vals})
