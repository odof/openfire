# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    def write(self, vals):
        res = super().write(vals)
        self.env['calendar.event'].action_update_date([('of_template_id', '=', self.id)])
        return res

    def unlink(self):
        self.env['calendar.event'].action_update_date([('of_template_id', '=', self.id)])
        return super().unlink()
