# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ---------------------------------------------------------
    # ORM methods
    # ---------------------------------------------------------

    def write(self, vals):
        partners_geodata_changed = self._get_partners_geodata_updated(vals)
        result = super().write(vals)
        if partners_geodata_changed:
            # if geodata has been changed, we need to recompute tours routes for interventions at these addresses
            partners_geodata_changed._handle_geodata_change()
        return result

    # ---------------------------------------------------------
    # Actions methods
    # ---------------------------------------------------------

    def action_button_open_tour_appointment_wizard(self):
        """
        Open the tour appointment wizard to plan an intervention for the partner.

        If the partner's address is not geocoded, a UserError is raised.

        The method checks the configuration parameters for quick scheduling and default planning task.
        If quick scheduling is disabled or no default planning task is set, the wizard is opened without pre-searching.
        Otherwise, the default values for the wizard are set based on the default planning task.

        Then the wizard is created and opened in a new window with pre-computed time slots.

        Returns:
            dict: action to open the tour appointment wizard form view

        Raises:
            UserError: if the partner's address is not geocoded
        """
        self.ensure_one()
        if not self.partner_latitude and not self.partner_longitude:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))

        icp_obj = self.env["ir.config_parameter"]
        tour_appointment_obj = self.env["of.tour.appointment.wizard"]
        context = self.env.context.copy()
        # In case we came from a wizard (for instance 'of.asterisk.number.not.found'),
        # we add partner id in context manually
        context["of_default_partner_id"] = self.id

        default_planning_intervention_template = icp_obj.sudo().get_param(
            "of.planning.tour.default_planning_intervention_template_id"
        )

        default_values = tour_appointment_obj.with_context(
            active_model=self._name,
            active_ids=self.ids,
        ).default_get(tour_appointment_obj._fields.keys())

        default_values.update(
            {
                "partner_id": self.id,
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

    # ---------------------------------------------------------
    # Business methods
    # ---------------------------------------------------------

    def _get_partners_geodata_updated(self, vals):
        """
        Returns a filtered recordset of partners whose geodata (latitude or longitude) has been updated.

        Args:
            vals (dict): dictionary of values to update

        Returns:
            recordset: filtered recordset of partners whose geodata has been updated
        """
        return self.filtered(
            lambda r: "partner_latitude" in vals
            and r.partner_latitude != vals["partner_latitude"]
            or "partner_longitude" in vals
            and r.partner_longitude != vals["partner_longitude"]
        )

    def _handle_geodata_change(self):
        """
        Handle changes in geodata for the partner.

        This method is responsible for handling changes in the geodata (latitude and longitude)
        of the partner. It invalidates the cache for partner_latitude and partner_longitude fields,
        and then recompute the tours that are associated with the partner and are not confirmed
        and not in the past.

        Returns:
            None
        """
        context = self.env.context.copy()
        self.invalidate_recordset(["partner_latitude", "partner_longitude"])

        if tours_to_recompute := (
            self.env["of.planning.tour"]
            .sudo()
            .with_context(**context)
            .search(
                [
                    ("state", "!=", "3-confirmed"),
                    ("date", ">=", fields.Date.today()),
                    "|",
                    "|",
                    ("start_address_id", "in", self.ids),
                    ("return_address_id", "in", self.ids),
                    ("tour_line_ids.address_id", "in", self.ids),
                ]
            )
        ):
            # Recompute geo data
            for line in tours_to_recompute.tour_line_ids.sorted("date_start"):
                line._update_line_data_from_intervention()
                line._compute_line_data()
                line._osrm_update_line_data()
                line.intervention_id.of_travel_duration = line.duration_one_way
            # Recompute available slots
            tours_to_recompute._reorganize_available_slot()
