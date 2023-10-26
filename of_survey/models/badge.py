# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class GamificationBadge(models.Model):
    _inherit = 'gamification.badge'

    of_survey_ids = fields.One2many(comodel_name='of.survey.survey', inverse_name='certification_badge_id')
    of_survey_id = fields.Many2one(
        comodel_name='of.survey.survey', string="Survey", compute='_compute_of_survey_id', store=True
    )

    @api.depends('of_survey_ids.certification_badge_id')
    def _compute_of_survey_id(self):
        for badge in self:
            badge.of_survey_id = badge.of_survey_ids[0] if badge.of_survey_ids else None
