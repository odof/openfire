# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class OFServiceRequest(models.Model):
    _inherit = 'of.service.request'

    def action_button_open_tour_appointment_wizard(self):
        """
        Open the tour appointment wizard to plan an intervention.

        This method is triggered when the user clicks on a button to open the tour appointment wizard.
        It checks if the address is geocoded and raises an error if it is not.
        It then creates a new tour appointment wizard with default values and computes the time slots.
        Finally, it returns an action to open the tour appointment wizard form view.

        Returns:
            dict: action to open the tour appointment wizard form view

        Raises:
            UserError: if the address is not geocoded
        """
        self.ensure_one()
        today = fields.Date.today()
        if self.address_id and not self.address_id.partner_latitude and not self.address_id.partner_longitude:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))
        if not self.next_date or not self.end_date:
            raise UserError(_("Please enter planning dates."))

        tour_appointment_obj = self.env['of.tour.appointment.wizard']
        icp_obj = self.env['ir.config_parameter']
        context = self.env.context.copy()

        default_planning_intervention_template = icp_obj.sudo().get_param(
            'of.planning.tour.default_planning_intervention_template_id'
        )
        default_values = tour_appointment_obj.with_context(
            active_model=self._name,
            active_ids=self.ids,
        ).default_get(tour_appointment_obj._fields.keys())

        next_date = today if self.next_date < today else self.next_date
        default_values.update(
            {
                'company_id': self.company_id.id,
                'partner_id': self.partner_id.id,
                'start_date_search': next_date,
                'search_period_in_days': 30 if self.end_date < today else (self.end_date - next_date).days + 1,
                'template_id': self.template_id.id or int(default_planning_intervention_template),
            }
        )

        tour_appointment_new = tour_appointment_obj.new(default_values)
        wizard_values = tour_appointment_obj._convert_to_write(tour_appointment_new._cache)
        tour_appointment_wizard = tour_appointment_obj.create(wizard_values)

        # start time slots computing
        tour_appointment_wizard._populate_line_ids()
        form_view_id = self.env.ref('of_planning_tour.of_tour_appointment_wizard_view_form').id
        return {
            'name': _("Plan intervention"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.tour.appointment.wizard',
            'views': [(form_view_id, 'form')],
            'res_id': tour_appointment_wizard.id,
            'target': 'current',
            'context': context,
        }
