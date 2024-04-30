# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    @api.model
    def _default_section_to_display_ids(self):
        section_to_display_ids = self.env['of.planning.intervention.section'].search([])
        return [Command.link(section_to_display.id) for section_to_display in section_to_display_ids]

    mobile = fields.Boolean(string="Mobile Intervention Template")
    section_to_display_ids = fields.Many2many(
        comodel_name='of.planning.intervention.section',
        relation='of_planning_intervention_template_section_rel',
        string="Sections to display on the intervention",
        default=lambda r: r._default_section_to_display_ids(),
    )

    def write(self, vals):
        res = super().write(vals)
        self.env['calendar.event'].action_update_date([('of_template_id', 'in', self.ids)])
        return res

    def unlink(self):
        self.env['calendar.event'].action_update_date([('of_template_id', 'in', self.ids)])
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
