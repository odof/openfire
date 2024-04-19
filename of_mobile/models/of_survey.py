# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class OFSurvey(models.Model):
    _inherit = 'of.survey.survey'

    def write(self, vals):
        res = super().write(vals)
        self.env['calendar.event'].action_update_date([('of_survey_id', 'in', self.ids)])
        return res

    def unlink(self):
        self.env['calendar.event'].action_update_date([('of_survey_id', 'in', self.ids)])
        return super().unlink()
