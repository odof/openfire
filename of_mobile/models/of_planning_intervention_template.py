# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class OFPlanningInterventionTemplate(models.Model):
    _inherit = "of.planning.intervention.template"

    @api.model
    def _default_section_to_display_ids(self):
        section_to_display_ids = self.env["of.planning.intervention.section"].search([])
        return [Command.link(section_to_display.id) for section_to_display in section_to_display_ids]

    section_to_display_ids = fields.Many2many(
        comodel_name="of.planning.intervention.section",
        relation="of_planning_intervention_template_section_rel",
        string="Sections to display on the intervention",
        default=lambda r: r._default_section_to_display_ids(),
    )
    send_reports = fields.Selection(
        selection_add=[("mobile", "Manual dispatch from Mobile")],
        help="* Manual dispatch: manually from the OpenFire web database.\n"
        "* Automatic dispatch at intervention closure: from the mobile app, as soon as the user"
        " clicks on 'Completed' in an intervention, the intervention becomes completed and the intervention"
        " report is automatically e-mailed to the customer.\n"
        "* Manual dispatch from mobile: from the mobile app, as soon as the user clicks on 'Completed'"
        " in an intervention, he can send the intervention report by e-mail to the customer.",
    )
    mobile_payment = fields.Boolean(string="Mobile payment")
    payment_mode_ids = fields.Many2many(
        comodel_name="of.payment.mode",
        string="Payment Mode",
        default=lambda self: self.env["of.payment.mode"].search([("payment_type", "=", "inbound")]).ids,
    )
    mobile_payment_fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position", string="Fiscal Position"
    )
    auto_confirm_invoice = fields.Boolean(string="Invoice Auto confirmation")

    @api.onchange("mobile_payment_fiscal_position_id")
    def onchange_mobile_payment_fiscal_position_id(self):
        self.fiscal_position_id = self.mobile_payment_fiscal_position_id

    def write(self, vals):
        res = super().write(vals)
        self.env["calendar.event"].action_update_date([("of_template_id", "in", self.ids)])
        return res

    def unlink(self):
        self.env["calendar.event"].action_update_date([("of_template_id", "in", self.ids)])
        return super().unlink()

    def action_button_toggle_mobile(self):
        self.ensure_one()
        default_template = self.env.ref(
            "of_planning.of_planning_default_intervention_template", raise_if_not_found=False
        )

        if default_template and self.id == default_template.id and self.mobile:
            raise UserError(_("The default template cannot be unpublished."))

        return super().action_button_toggle_mobile()

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = super()._prepare_graphql_domain(select, domain)

        if select and "mobile" in select:
            odoo_domain += [("mobile", "=", select.mobile)]

        return odoo_domain
