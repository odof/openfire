# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, fields, models
from odoo.exceptions import UserError


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    mobile = fields.Boolean(string="Mobile Intervention Template")

    def write(self, vals):
        res = super().write(vals)
        self.env['calendar.event'].action_update_date([('of_template_id', '=', self.id)])
        return res

    def unlink(self):
        self.env['calendar.event'].action_update_date([('of_template_id', '=', self.id)])
        return super().unlink()

    def action_button_toggle_mobile(self):
        self.ensure_one()
        default_template = self.env.ref(
            'of_planning.of_planning_default_intervention_template', raise_if_not_found=False
        )

        if default_template and self.id == default_template.id and self.mobile:
            raise UserError(_("The default template cannot be unpublished."))

        self.mobile = not self.mobile
        if self.mobile and self.task_id:
            self.task_id.mobile = True
