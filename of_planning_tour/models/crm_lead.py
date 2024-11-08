# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def action_button_open_tour_appointment_wizard(self):
        """
        Open the tour appointment wizard to plan an intervention for the lead.

        If the lead partner's address is not geocoded, a UserError is raised.

        The method checks the configuration parameters for quick scheduling and default planning task.
        If quick scheduling is disabled or no default planning task is set, the wizard is opened without pre-searching.
        Otherwise, the default values for the wizard are set based on the default planning task.

        Then the wizard is created and opened in a new window with pre-computed time slots.

        Returns:
            dict: action to open the tour appointment wizard form view

        Raises:
            UserError: if the lead partner's address is not geocoded
        """
        self.ensure_one()
        if not self.partner_id.partner_latitude and not self.partner_id.partner_longitude:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))

        icp_obj = self.env["ir.config_parameter"]
        tour_appointment_obj = self.env["of.tour.appointment.wizard"]
        context = self.env.context.copy()
        # In case we came from a wizard (for instance 'of.asterisk.number.not.found'),
        # we add partner id in context manually
        context["of_default_partner_id"] = self.partner_id.id

        default_planning_intervention_template = icp_obj.sudo().get_param(
            "of.planning.tour.default_planning_intervention_template_id"
        )

        default_values = tour_appointment_obj.with_context(
            active_model=self._name,
            active_ids=self.ids,
        ).default_get(tour_appointment_obj._fields.keys())

        default_values.update(
            {
                "partner_id": self.partner_id.id,
                "search_period_in_days": 8,
                "template_id": int(default_planning_intervention_template),
                "company_id": self.company_id.id or self.env.company.id,
            }
        )
        tour_appointment_wizard = tour_appointment_obj.create(default_values)
        # start time slots computing
        tour_appointment_wizard._populate_line_ids()
        form_view_id = self.env.ref("of_planning_tour.of_tour_appointment_wizard_view_form").id
        return {
            "name": _("Plan intervention"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "of.tour.appointment.wizard",
            "views": [(form_view_id, "form")],
            "res_id": tour_appointment_wizard.id,
            "target": "current",
            "context": context,
        }
