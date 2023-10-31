# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveyUserInput(models.Model):
    _inherit = 'of.survey.user_input'

    of_crm_lead_id = fields.Many2one('crm.lead', string='Lead')
