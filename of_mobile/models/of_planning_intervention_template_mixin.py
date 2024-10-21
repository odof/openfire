# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplateMixin(models.AbstractModel):
    _inherit = "of.planning.intervention.template.mixin"

    mobile = fields.Boolean(string="Mobile Intervention Template")
    additional_line_ids = fields.One2many(
        comodel_name="of.planning.intervention.template.additional.line",
        inverse_name="additional_template_id",
        string="Additional Invoice lines",
    )

    def action_button_toggle_mobile(self):
        self.ensure_one()
        self.mobile = not self.mobile
        if self.mobile and self.task_id:
            self.task_id.mobile = True
