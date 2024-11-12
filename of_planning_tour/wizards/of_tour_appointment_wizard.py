# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import date, timedelta

import requests
from babel.dates import format_date

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.of_utils.models.misc import distance_between_points

from ..models.of_planning_available_slot import SELECTION_DAY_PERIOD
from ..models.of_planning_tour import DEFAULT_AM_LIMIT_FLOAT
from ..models.res_config_settings import SELECTION_SEARCH_MODES, SELECTION_SEARCH_TYPES

_logger = logging.getLogger(__name__)


class OFTourAppointmentWizard(models.TransientModel):
    _name = "of.tour.appointment.wizard"
    _description = "Appointment scheduling for tours"

    @api.model
    def default_get(self, field_list=None):
        default_values = super().default_get(field_list)
        active_model = self.env.context.get("active_model", "")
        context = self.env.context
        if active_model == "res.partner":
            self._handle_default_get_res_partner(context, default_values)
        elif active_model == "crm.lead":
            self._handle_default_get_crm_lead(context, default_values)
        elif active_model == "calendar.event":
            self._handle_default_get_calendar_event(context, default_values)
        elif active_model == "of.service.request":
            self._handle_default_get_service_request(context, default_values)
        elif active_model == "sale.order":
            self._handle_default_get_sale_order(context, default_values)
        elif context.get("of_default_partner_id"):
            self._handle_default_get_default_partner(context, default_values)

        self._default_get_update_address_if_needed(default_values)
        self._default_get_set_start_stop_dates(default_values)

        if context.get("of_from_portal"):
            return default_values

        self._default_get_apply_search_template(default_values)

        return default_values

    @api.model
    def _default_day_ids(self):
        # added sudo() to avoid access rights issues from the website (no access for of.planning.tour)
        days = self.env["of.days"].sudo().search([("number", "in", (1, 2, 3, 4, 5))], order="number")
        return [day.id for day in days]

    @api.model
    def _default_search_mode(self):
        return self.env["ir.config_parameter"].sudo().get_param("of.planning.tour.search_mode") or "oneway_or_return"

    @api.model
    def _default_search_type(self):
        return self.env["ir.config_parameter"].sudo().get_param("of.planning.tour.search_type") or "duration"

    @api.model
    def _default_planning_intervention_template(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of.planning.tour.default_planning_intervention_template_id")
        )

    @api.model
    def _get_domain_search_template_id(self):
        return ["|", ("access_user_ids", "=", False), ("access_user_ids", "in", self._uid)]

    @api.model
    def _get_domain_pre_employee_ids(self):
        return ["|", ("access_user_ids", "=", False), ("access_user_ids", "in", self._uid)]

    source_model = fields.Char(readonly=True)

    # == Search fields ==
    search_template_id = fields.Many2one(
        comodel_name="of.tour.appointment.template",
        string="Search Template",
        domain=lambda self: self._get_domain_search_template_id(),
    )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer", required=True, readonly=True)
    partner_email = fields.Char(related="partner_id.email")
    partner_mobile = fields.Char(related="partner_id.mobile")
    partner_phone = fields.Char(related="partner_id.phone")
    partner_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Intervention Address",
        required=True,
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]",
    )
    geo_lat = fields.Float(related="partner_address_id.partner_latitude", readonly=True)
    geo_lng = fields.Float(related="partner_address_id.partner_longitude", readonly=True)
    ignore_geodata = fields.Boolean()
    partner_address_street = fields.Char(related="partner_address_id.street", readonly=True)
    partner_address_street2 = fields.Char(related="partner_address_id.street2", readonly=True)
    partner_address_city = fields.Char(related="partner_address_id.city", readonly=True)
    partner_address_state_id = fields.Many2one(related="partner_address_id.state_id", readonly=True)
    partner_address_zip = fields.Char(related="partner_address_id.zip", readonly=True)
    partner_address_country_id = fields.Many2one(related="partner_address_id.country_id", readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        compute="_compute_company_id",
        required=True,
        store=True,
        readonly=False,
    )
    request_id = fields.Many2one(
        comodel_name="of.service.request", string="Service Request", domain="[('partner_id', '=', partner_id)]"
    )
    intervention_id = fields.Many2one(comodel_name="calendar.event", string="Intervention")
    task_id = fields.Many2one(
        comodel_name="of.planning.task", string="Task", compute="_compute_task_id", store=True, readonly=False
    )
    template_id = fields.Many2one(
        comodel_name="of.planning.intervention.template",
        string="Intervention Template",
        default=lambda s: s._default_planning_intervention_template(),
    )
    duration = fields.Float(compute="_compute_duration", store=True, readonly=False)
    pre_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Operator(s)",
        domain="""['&', '|', ('of_is_operator', '=', True), ('of_is_salesperson', '=', True),
         '|', ('of_task_ids', 'in', task_id), ('of_all_tasks', '=', True)]""",
        help="Pre-select operators",
    )
    start_date_search = fields.Date(string="From", required=True, default=lambda *a: (date.today() + timedelta(days=1)))
    stop_date_search = fields.Date(string="To", compute="_compute_stop_date_search")
    search_type = fields.Selection(
        selection=SELECTION_SEARCH_TYPES,
        required=True,
        default=lambda s: s._default_search_type(),
    )
    search_mode = fields.Selection(
        selection=SELECTION_SEARCH_MODES,
        required=True,
        default=lambda s: s._default_search_mode(),
    )
    search_period_in_days = fields.Integer(string="Search period (in days)", default=30, required=True)
    day_ids = fields.Many2many(
        comodel_name="of.days",
        relation="wizard_plan_intervention_days_rel",
        column1="wizard_id",
        column2="day_id",
        string="Days",
        required=True,
        default=lambda s: s._default_day_ids(),
    )
    day_period = fields.Selection(selection=SELECTION_DAY_PERIOD, default="both", required=True)
    orthodromic = fields.Boolean(string="Distance as the crow flies")

    # == Results fields ==
    line_ids = fields.One2many(
        comodel_name="of.tour.appointment.line.wizard", inverse_name="wizard_id", string="Slots Proposals"
    )
    by_distance_line_ids = fields.One2many(
        comodel_name="of.tour.appointment.line.wizard",
        compute="_compute_by_distance_line_ids",
        string="Slots by distance",
    )
    by_duration_line_ids = fields.One2many(
        comodel_name="of.tour.appointment.line.wizard",
        compute="_compute_by_duration_line_ids",
        string="Slots by duration",
    )
    by_date_line_ids = fields.One2many(
        comodel_name="of.tour.appointment.line.wizard", compute="_compute_by_date_line_ids", string="Slots by date"
    )
    selected_line_id = fields.Many2one(comodel_name="of.tour.appointment.line.wizard", string="Selected Slot")

    name = fields.Char(size=64, required=False)
    description = fields.Text()
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Operator")
    selected_datetime = fields.Datetime()
    # fields for creation/update of recurrent interventions
    next_date = fields.Date(string="Next intervention", help="Date from which to schedule next service")
    planning_end_date = fields.Date(help="Date from which intervention becomes overdue")
    flexible = fields.Boolean(string="Include Flexible Appointment", help="Show flexible appointment slots as free")

    # == Maps fields ==
    map_line_id = fields.Many2one(
        comodel_name="of.tour.appointment.line.wizard", string="Line selected for the map preview"
    )
    map_tour_id = fields.Many2one(comodel_name="of.planning.tour", string="Tour")
    additional_records = fields.Char(
        string="Data for displaying additional records", compute="_compute_additional_records_data"
    )
    additional_record_geometry_data = fields.Text(
        string="Geojson data",
        compute="_compute_additional_records_data",
        help="Geojson data used to draw the route on the map between the meeting we are trying to plan and "
        "the previous/next coordinates",
    )
    map_tour_line_ids = fields.One2many(
        comodel_name="of.planning.tour.line", string="Tour lines", compute="_compute_map_data"
    )
    start_address_id = fields.Many2one(comodel_name="res.partner", compute="_compute_map_data")
    return_address_id = fields.Many2one(comodel_name="res.partner", compute="_compute_map_data")
    map_latitude = fields.Text(compute="_compute_map_data")
    map_longitude = fields.Text(compute="_compute_map_data")

    lead_id = fields.Many2one(comodel_name="crm.lead", string="Opportunité")

    # --------------------------------------------------------------------------
    # Constraints methods
    # --------------------------------------------------------------------------

    @api.constrains("search_period_in_days")
    def _check_search_period_in_days(self):
        if self.search_period_in_days < 1 or self.search_period_in_days > 45:
            raise ValidationError(_("The value of 'Search period (in days)' must be between 1 and 45."))

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("partner_address_id")
    def _compute_company_id(self):
        for wizard in self:
            if wizard.request_id:
                wizard.company_id = wizard.request_id.company_id
            elif wizard.intervention_id:
                wizard.company_id = wizard.intervention_id.company_id
            else:
                company_choice = self.env.user.company_id.of_company_choice or "contact"  # 'user' or 'contact'
                wizard.company_id = (
                    wizard.partner_address_id.company_id
                    if company_choice == "contact" and wizard.partner_address_id.company_id
                    else self.env.user.company_id
                )

    @api.depends("line_ids", "line_ids.useful_distance")
    def _compute_by_distance_line_ids(self):
        for wizard in self:
            wizard.by_distance_line_ids = wizard.line_ids.sorted("useful_distance")

    @api.depends("line_ids", "line_ids.useful_duration")
    def _compute_by_duration_line_ids(self):
        for wizard in self:
            wizard.by_duration_line_ids = wizard.line_ids.sorted("useful_duration")

    @api.depends("line_ids", "line_ids.start")
    def _compute_by_date_line_ids(self):
        for wizard in self:
            wizard.by_date_line_ids = wizard.line_ids.sorted("start")

    @api.depends(
        "map_line_id",
        "geo_lat",
        "geo_lng",
        "partner_id",
        "request_id",
        "request_id.partner_latitude",
        "request_id.partner_longitude",
        "intervention_id",
        "intervention_id.of_partner_latitude",
        "intervention_id.of_partner_longitude",
    )
    def _compute_additional_records_data(self):
        """Builds a list of dict to display additional records on the map, containing information about the field
        operation to be planned.
        """
        for wizard in self:
            additionnal_record = wizard.request_id or wizard.intervention_id or wizard.partner_id
            if not additionnal_record:
                wizard.additional_records = json.dumps({})
                wizard.additional_record_geometry_data = json.dumps({})
                continue

            records = []
            if wizard.map_tour_id:
                start_marker, end_marker = wizard.map_tour_id._get_start_stop_markers_data_for_tour()
                records.extend([start_marker, end_marker])

            date_preview = wizard.map_line_id.start or False
            records.append(
                {
                    "id": f"fake_record_{additionnal_record.id}",
                    "is_service_request": True,
                    "address_city": wizard.partner_address_city,
                    "partner_name": wizard.partner_id.name,
                    "tour_number": _("SR"),
                    "geo_lng": wizard.geo_lng,
                    "geo_lat": wizard.geo_lat,
                    "partner_phone": wizard.partner_id.phone,
                    "partner_mobile": wizard.partner_id.mobile,
                    "task_name": wizard.task_id.name,
                    "date": str(date_preview),
                    "address_zip": wizard.partner_address_zip,
                }
            )
            wizard.additional_records = json.dumps(records)
            wizard.additional_record_geometry_data = self._get_additional_record_geometry_data(wizard.map_line_id)

    @api.depends("selected_line_id", "map_tour_id", "map_line_id")
    def _compute_map_data(self):
        for wizard in self:
            tour = wizard.map_tour_id
            addresses_values = self.env["of.planning.tour"]._process_address_values(
                {
                    "employee_id": wizard.selected_line_id.employee_id.id,
                    "start_address_id": tour.start_address_id.id or False,
                    "return_address_id": tour.return_address_id.id or False,
                }
            )
            wizard.start_address_id = addresses_values.get("start_address_id")
            wizard.return_address_id = addresses_values.get("return_address_id")
            wizard.map_latitude = tour.map_latitude if tour else wizard.start_address_id.partner_latitude
            wizard.map_longitude = tour.map_longitude if tour else wizard.return_address_id.partner_longitude
            wizard.map_tour_line_ids = tour.tour_line_ids if tour else False

    @api.depends("start_date_search", "search_period_in_days")
    def _compute_stop_date_search(self):
        for wizard in self:
            if wizard.start_date_search:
                period_in_days = wizard.search_period_in_days or 30
                wizard.stop_date_search = wizard.start_date_search + timedelta(days=period_in_days - 1)
            else:
                wizard.stop_date_search = False

    @api.depends("template_id")
    def _compute_task_id(self):
        for wizard in self:
            wizard.task_id = wizard.template_id.task_id if wizard.template_id else False

    @api.depends("task_id")
    def _compute_duration(self):
        for wizard in self:
            wizard.duration = wizard.task_id.duration if wizard.task_id else 0.0

    # --------------------------------------------------------------------------
    # Onchange methods
    # --------------------------------------------------------------------------

    @api.onchange("search_template_id")
    def _onchange_search_template_id(self):
        if not self.search_template_id:
            return

        vals = {}
        if self.search_template_id.employee_ids:
            vals["pre_employee_ids"] = [Command.set([emp.id for emp in self.search_template_id.employee_ids])]
        if self.search_template_id.task_id and not self.task_id:
            vals["task_id"] = self.search_template_id.task_id.id
        if self.search_template_id.template_id and not self.template_id:
            vals["template_id"] = self.search_template_id.template_id.id
        if self.search_template_id.search_mode:
            vals["search_mode"] = self.search_template_id.search_mode
        if self.search_template_id.search_type:
            vals["search_type"] = self.search_template_id.search_type

        self.update(vals)

    # --------------------------------------------------------------------------
    # Action methods
    # --------------------------------------------------------------------------

    def action_button_search(self):
        """Launch the search for available slots"""
        self.ensure_one()
        if self.partner_address_id.of_geocoding_state in ["not_tried", "failure", "no_address"]:
            raise UserError(_("Intervention address is not geolocated."))
        if not self.template_id:
            raise UserError(_("Please enter an intervention template to start the slot search."))
        # empty the current selected tour for the map
        if self.map_tour_id:
            self.map_tour_id = False
        # empty the current selected line for the map
        if self.map_line_id:
            self.map_line_id = False
        self._populate_line_ids()

    def action_button_confirm(self):
        """Create intervention and open it in form view. Also create a recurrent intervention if needed."""
        self.ensure_one()
        context = self.env.context.copy()
        event_obj = self.env["calendar.event"]

        self.update(self.selected_line_id._prepare_wizard_values())

        values = self._prepare_calendar_event_values()
        event = event_obj.create(values)
        event._compute_of_employee_ids()

        if self.request_id and self.next_date:
            self.request_id.write({"next_date": self.next_date, "end_date": self.planning_end_date})
        return {
            "type": "ir.actions.act_window",
            "res_model": "calendar.event",
            "view_type": "form",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": event.id,
            "target": "current",
            "context": context,
            "flags": {"initial_mode": "edit", "form": {"options": {"mode": "edit"}}},
        }

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _handle_default_get_res_partner(self, context, default_values):
        """
        Handle the default get operation for the `res.partner` model.

        Args:
            context (dict): The context dictionary.
            default_values (dict): The default values dictionary.

        Returns:
            None
        """
        partner_obj = self.env["res.partner"]
        partner_id = context["active_ids"][0]
        partner = partner_obj.browse(partner_id)
        request = self.env["of.service.request"].search(
            [("partner_id", "=", partner.id), ("recurrency", "=", True)], limit=1
        )
        address = partner_obj.browse(partner.address_get(["delivery"])["delivery"])
        self._default_get_update_default_values(default_values, "res.partner", partner, address, request)

    def _handle_default_get_crm_lead(self, context, default_values):
        """
        Handle the default get operation for the `crm.lead` model.

        Args:
            context (dict): The context dictionary.
            default_values (dict): The default values dictionary.

        Returns:
            None
        """
        lead_obj = self.env["crm.lead"]
        lead_id = context["active_ids"][0]
        lead = lead_obj.browse(lead_id)
        self._default_get_update_default_values(
            default_values, "crm.lead", lead.partner_id, lead.partner_id, False, False, lead
        )

    def _handle_default_get_calendar_event(self, context, default_values):
        """
        Handle the default get operation for the `calendar.event` model.

        Args:
            context (dict): The context dictionary.
            default_values (dict): The default values dictionary.

        Returns:
            None
        """
        active_model = "calendar.event"
        active_record_id = context["active_ids"][0]
        active_record = self.env[active_model].browse(active_record_id)
        partner = active_record.of_partner_id
        address = active_record.of_address_id
        event = active_record
        request = event.of_request_id
        default_values["pre_employee_ids"] = [Command.set([emp.id for emp in active_record.of_employee_ids])]
        self._default_get_update_default_values(default_values, active_model, partner, address, request, event)

    def _handle_default_get_service_request(self, context, default_values):
        """
        Handle the default get operation for the `of.service.request` model.

        Args:
            context (dict): The context dictionary.
            default_values (dict): The default values dictionary.

        Returns:
            None
        """
        active_model = "of.service.request"
        active_record_id = context["active_ids"][0]
        active_record = self.env[active_model].browse(active_record_id)
        partner = active_record.partner_id
        address = active_record.address_id
        request = active_record
        default_values["pre_employee_ids"] = [Command.set([emp.id for emp in active_record.employee_ids])]
        self._default_get_update_default_values(default_values, active_model, partner, address, request)

    def _handle_default_get_sale_order(self, context, default_values):
        """
        Handle the default get operation for the `sale.order` model.

        Args:
            context (dict): The context dictionary.
            default_values (dict): The default values dictionary.

        Returns:
            None
        """
        active_model = "sale.order"
        order_id = context["active_ids"][0]
        order = self.env[active_model].browse(order_id)
        partner = order.partner_id
        request = self.env["of.service.request"].search([("order_id", "=", order_id)], limit=1) or self.env[
            "of.service.request"
        ].search([("partner_id", "=", partner.id)], limit=1)
        address = order.partner_shipping_id or order.partner_id
        self._default_get_update_default_values(default_values, active_model, partner, address, request)

    def _handle_default_get_default_partner(self, context, default_values):
        """
        Handle the default values for the default partner.

        Args:
            context (dict): The context dictionary.
            default_values (dict): The default values dictionary.

        Returns:
            None
        """
        active_model = "res.partner"
        partner_obj = self.env[active_model]
        partner_id = context.get("of_default_partner_id")
        partner = partner_obj.browse(partner_id)
        request = self.env["of.service.request"].search(
            [("partner_id", "=", partner.id), ("recurrency", "=", True)], limit=1
        )
        address = partner_obj.browse(partner.address_get(["delivery"])["delivery"])
        self._default_get_update_default_values(default_values, active_model, partner, address, request)

    def _default_get_update_default_values(
        self, default_values, active_model, partner, address, request, event=False, lead=False
    ):
        default_values.update(
            {
                "source_model": active_model,
                "partner_id": partner.id or False,
                "partner_address_id": address and address.id or partner.id or False,
                "request_id": request and request.id or False,
                "intervention_id": event and event.id or False,
                "lead_id": lead and lead.id or False,
            }
        )
        if request:
            default_values["day_ids"] = [Command.set(request.day_ids.ids)]

    def _default_get_update_address_if_needed(self, default_values):
        """
        Update the address if needed based on the partner's location.

        Args:
            default_values (dict): The dictionary to be updated.

        Returns:
            None
        """
        partner_obj = self.env["res.partner"]
        address = partner_obj.browse(default_values.get("partner_address_id"))
        partner = partner_obj.browse(default_values.get("partner_id"))
        if address and not address.partner_latitude and not address.partner_longitude:
            address = (
                partner_obj.search(
                    [
                        "|",
                        ("id", "=", partner.id),
                        ("parent_id", "=", partner.id),
                        "|",
                        ("geo_lat", "!=", 0),
                        ("geo_lng", "!=", 0),
                    ],
                    limit=1,
                )
                or address
            )
            default_values["partner_address_id"] = address.id

    def _default_get_set_start_stop_dates(self, default_values):
        """
        Sets the start and stop dates for the appointment based on the given parameters.

        Args:
            default_values (dict): The dictionary to be updated.

        Returns:
            None
        """
        request = self.env["of.service.request"].browse(default_values.get("request_id"))
        if self.env["calendar.event"].browse(default_values.get("intervention_id")):
            default_values["start_date_search"] = fields.Date.today()
        elif request and request.next_date and request.next_date >= fields.Date.today():
            default_values["start_date_search"] = request.next_date
            default_values["stop_date_search"] = request.end_date

    def _default_get_apply_search_template(self, default_values):
        """
        Apply the default search template to the given result dictionary.

        Args:
            default_values (dict): The dictionary to be updated.

        Returns:
            None
        """
        if not (
            search_template := self.env["of.tour.appointment.template"].search(
                [("default_user_ids", "in", self._uid)], limit=1
            )
        ):
            return
        if search_template.employee_ids and "pre_employee_ids" not in default_values:
            default_values["pre_employee_ids"] = [Command.set([emp.id for emp in search_template.employee_ids])]
        if search_template.task_id:
            default_values["task_id"] = search_template.task_id.id
        if search_template.template_id:
            default_values["template_id"] = search_template.template_id.id
        if search_template.search_mode:
            default_values["search_mode"] = search_template.search_mode
        if search_template.search_type:
            default_values["search_type"] = search_template.search_type
        default_values["search_template_id"] = search_template.id

    @api.model
    def _get_additional_record_geometry_data(self, line):
        """
        Get the additional geojson data for the current intervention we are planning which will be added to the
        tour route.

        That data will be used to display the route to go to the intervention on the map within the current tour route.

        Args:
            line (of.tour.appointment.line.wizard): The line object representing the intervention.

        Returns:
            str: The geojson data representing the route to the intervention or False if the data is not available.
        """
        tour = line.tour_id
        previous_geo_lat = line.previous_geo_lat
        previous_geo_lng = line.previous_geo_lng
        next_geo_lat = line.next_geo_lat
        next_geo_lng = line.next_geo_lng
        if not tour or not previous_geo_lat or not previous_geo_lng or not next_geo_lat or not next_geo_lng:
            return False

        osrm_base_url = tour and tour._osrm_get_base_url() or False
        geometry_data = False
        coords_str = (
            f"{line.previous_geo_lng},{line.previous_geo_lat};{line.wizard_id.geo_lng},"  # noqa
            f"{line.wizard_id.geo_lat};{line.next_geo_lng},{line.next_geo_lat}"  # noqa
        )
        full_query = f"{osrm_base_url}/{coords_str}?geometries=geojson&steps=true&overview=false"
        steps, _null, _null = self.env["of.planning.tour.line"]._osrm_get_steps_data(full_query)
        geometry_data = [step["geometry"] for step in steps]
        geometry_data = geometry_data and json.dumps(geometry_data)
        return geometry_data

    def _get_potential_employee_ids(self):
        self.ensure_one()
        employee_ids = []
        for planning in self.line_ids:
            if planning.employee_id.id not in employee_ids:
                employee_ids.append(planning.employee_id.id)
        return employee_ids

    def _get_tour_dates(self, web=False):
        """
        Returns a list of tour dates between the start_date and stop_date of the wizard that are the right days.

        Returns:
            list: A list of tour dates as strings.
        """
        self.ensure_one()

        # To only create tour or display slot from the selected days
        days = web and self.day_ids.sudo() or self.day_ids
        selected_days = days.mapped(lambda d: d.number - 1)

        start_date = self.start_date_search
        if not start_date:
            return []

        end_date = self.stop_date_search
        res = []
        if end_date != start_date:  # If the event is split over multiple days
            eval_date = start_date
            while eval_date <= end_date:
                if eval_date.weekday() in selected_days:
                    res.append(eval_date)
                eval_date += timedelta(days=1)

        return [fields.Date.to_string(date) for date in res]

    def _populate_line_ids(self, web=False, mode="new", sector_id=False):
        """
        Remplit le champ line_ids avec les créneaux disponibles.
        Lance le calcul des distances et sélectionne un résultat si il y en a
        web=True quand recherche de créneau depuis le site web.
        """
        self.ensure_one()

        tour_obj = self.env["of.planning.tour"]
        employee_obj = self.env["hr.employee"]
        available_slot_obj = self.env["of.planning.available.slot"]
        event_obj = self.with_context(force_read=True).env["calendar.event"]

        # To avoid an access error from the website
        company = self.company_id.sudo() if web else self.company_id
        if not company.partner_id.partner_latitude and not company.partner_id.partner_longitude:
            raise UserError(
                _(
                    "The company address is not geocoded, please geocode it to plan an intervention. "
                    "If an employee's address is not geocoded, we will use the company address instead "
                    "to plan the intervention."
                )
            )

        if web:
            employee_obj = employee_obj.sudo()
            event_obj = event_obj.sudo()
            available_slot_obj = available_slot_obj.sudo()
            tour_obj = tour_obj.sudo()

        dates_eval = self._get_tour_dates(web=web)
        address = web and self.partner_address_id.sudo() or self.partner_address_id
        address_sector = address.of_tech_sector_id

        # Get employees who can carry out the task
        task_id = web and self.task_id.sudo() or self.task_id
        pre_employee_ids = web and self.sudo().pre_employee_ids or self.pre_employee_ids
        if task_id and not task_id.employee_ids:
            if not web:
                raise UserError(_("This service cannot be carried out by any operator"))

            _logger.warning(
                f"Unsuccessful attempt to find a slot for the task '{task_id.name}': no one can carry it out."
            )
            return
        capable_employees = employee_obj.search(["|", ("of_is_operator", "=", True), ("of_is_salesperson", "=", True)])
        # Filter employees by ability
        if task_id:
            capable_employees &= task_id.employee_ids
        # If there are operators provided
        if pre_employee_ids or web:
            capable_employees &= pre_employee_ids

        # Create tours for employees if needed
        tour_obj._create_tours_for_employees(capable_employees, dates_eval, address_sector)

        # Delete old lines
        if mode == "new":
            self.line_ids.unlink()

        # The basic search domain
        search_domain = [("date", "in", dates_eval)]

        search_domain += [("employee_id", "in", capable_employees.ids)]

        # If there is a duration  provided
        if self.duration:
            search_domain += [("duration", ">=", self.duration)]

        # If there is a period of the day provided
        if self.day_period != "both":
            search_domain += [("day_period", "=", self.day_period)]

        # Get the employees' availability
        available_slots = available_slot_obj.search(search_domain)

        # Create wizard lines
        self._create_line_ids(available_slots, web=web)

        if not self.ignore_geodata:
            try:
                res = tour_obj._osrm_test_connection()
                if res:
                    self.orthodromic = False
            except Exception:
                self.orthodromic = True
            self._calculate_distance_and_duration(web=web)
            self._unlink_line_too_far()
            self._select_first_line()
            self._handle_first_line()

    def _create_line_ids(self, available_slots, web=False):
        wizard_line_obj = self.env["of.tour.appointment.line.wizard"]

        for slot in available_slots:
            wizard_line_obj.create(
                {
                    "available_slot_id": slot.id,
                    "wizard_id": self.id,
                    "template_id": self.template_id.id,
                }
            )

    def _unlink_line_too_far(self):
        """
        Unlink the lines that, once the distance and duration calculated, are too far to fit in their available slots.
        """
        self.line_ids.filtered(
            lambda li: li.wizard_id.duration + (li.useful_duration / 60) > li.available_slot_id.duration
        ).unlink()

    def _select_first_line(self):
        """Mark the first line as the best line"""
        if lines := self.line_ids.sorted("useful_distance"):
            lines[0].best = True
            lines[0].selected = True
            lines[0].wizard_id.selected_line_id = lines[0]

    def _handle_first_line(self):
        """Handle the first line"""
        if not self.selected_line_id:
            return

        self.map_line_id = self.selected_line_id
        self.map_tour_id = self.selected_line_id and self.selected_line_id.tour_id.id or False
        self.additional_record_geometry_data = self._get_additional_record_geometry_data(self.map_line_id)

    def _prepare_service_request_values(self, month):
        """
        Prepare the values for creating a recurring service request.

        Args:
            month (int): The reference month for the recurring intervention.

        Returns:
            dict: The values for creating a service request.
        """
        return {
            "partner_id": self.partner_id.id,
            "address_id": self.partner_address_id.id,
            "company_id": self.company_id.id,
            "task_id": self.task_id.id,
            "type_id": self.env.ref("of_service.of_service_request_type_maintenance").id,
            "month_ids": [Command.link(month)],
            "next_date": self.next_date,
            "end_date": self.planning_end_date,
            "note": self.description or "",
            "base_state": "draft",
            "duration": self.duration,
            "recurrency": True,
            "template_id": self.template_id.id,
        }

    def _prepare_calendar_event_values(self):
        """
        Prepare the dictionary of values for creating the Tech Appointment.

        Returns:
            dict: Dictionary of values for creating the Tech Appointment.
        """
        self.ensure_one()
        request = self.request_id
        template = self.selected_line_id.template_id

        tag_ids = []
        if self.intervention_id:
            tag_ids = [Command.set(self.intervention_id.of_tag_ids.ids)]
        elif request:
            tag_ids = [Command.set(request.tag_ids.ids)]

        order_id = self.intervention_id.of_order_id.id if self.intervention_id else request.order_id.id
        picking_list = (
            self.intervention_id.of_order_id.picking_ids.ids
            if self.intervention_id
            else request.order_id.picking_ids.ids
        )
        name = self.intervention_id.name if self.intervention_id else self.name
        previous_duration = self.selected_line_id.previous_duration / 60
        values = {
            "of_partner_id": self.partner_id.id,
            "of_address_id": self.partner_address_id.id,
            "of_task_id": self.task_id.id,
            "of_template_id": template.id,
            "of_request_id": request.id,
            "of_employee_id": self.employee_id.id,
            "of_employee_ids": [Command.link(self.employee_id.id)],
            "of_tag_ids": tag_ids,
            "start": self.selected_datetime + timedelta(hours=previous_duration),
            "stop": self.selected_datetime + timedelta(hours=(self.duration + previous_duration)),
            "of_travel_duration": previous_duration,
            "user_id": self._uid,
            "of_company_id": self.company_id.id,
            "name": name,
            "description": self.description or "",
            "of_state": "confirmed",
            "of_order_id": order_id,
            "of_picking_manual_ids": len(picking_list) == 1 and picking_list[0] or False,
            "of_type": "intervention",
            "of_type_id": template.type_id.id,
            "of_lead_id": self.lead_id.id,
        }
        if self.intervention_id:
            copied_lines = []
            for line in self.intervention_id.of_line_ids:
                line_values = line.copy_data()[0]
                line_values.update({"intervention_id": False})
                copied_lines.append(Command.create(line_values))

            copied_questions = []
            for question in self.intervention_id.of_question_ids:
                question_values = question.copy_data()[0]
                question_values.update({"intervention_id": False})
                copied_questions.append(Command.create(question_values))

            values |= {
                "of_line_ids": copied_lines,
                "of_question_ids": copied_questions,
                "of_team_id": self.intervention_id.of_team_id.id,
                "of_type_id": self.intervention_id.of_type_id.id,
                "of_equipment_ids": self.intervention_id.of_equipment_ids.ids,
                "of_picking_manual_ids": [Command.set(self.intervention_id.of_picking_manual_ids.ids)],
                "of_invoice_policy": self.intervention_id.of_invoice_policy,
                "of_fiscal_position_id": self.intervention_id.of_fiscal_position_id.id,
                "of_internal_description": self.intervention_id.of_internal_description or "",
            }

        return values

    def _calculate_distance_and_duration(self, web=False):
        """
        This method calculates the distance and duration between the available time slots and existing appointments
        by calling the OSRM openfire server.
        """
        self.ensure_one()
        wizard_line_obj = self.env["of.tour.appointment.line.wizard"]
        tour_obj = self.env["of.planning.tour"]

        lines = wizard_line_obj.search([("wizard_id", "=", self.id)], order="start")
        for line in lines:
            line = web and line.sudo() or line
            tour = line.tour_id
            employee = line.employee_id
            origin = tour.start_address_id
            arrival = tour.return_address_id
            # Pas d'origine ni pour la tournée ni pour l'employé
            if not origin:
                raise UserError(_('The operator "%(name)s" has no starting address.'), name=employee.name)
            # Pas d'arrivée ni pour la tournée ni pour l'employé
            elif not arrival:
                raise UserError(_('The operator "%(name)s" has no return address.'), name=employee.name)
            elif origin.partner_latitude == origin.partner_longitude == 0:
                raise UserError(
                    _('Operator\'s starting address "%(name)s" is not geolocated.\nDate : %(date)s'),
                    name=employee.name,
                    date=line.date,
                )
            elif arrival.partner_latitude == arrival.partner_longitude == 0:
                raise UserError(
                    _('Operator\'s return address "%(name)s" is not geolocated.\nDate : %(date)s'),
                    name=employee.name,
                    date=line.date,
                )

            if self.orthodromic:
                previous_dist = distance_between_points(
                    line.wizard_id.geo_lat, line.wizard_id.geo_lng, line.previous_geo_lat, line.previous_geo_lng
                )
                next_dist = distance_between_points(
                    line.wizard_id.geo_lat, line.wizard_id.geo_lng, line.next_geo_lat, line.next_geo_lng
                )
                line.update(
                    {
                        "distance": (previous_dist + next_dist),
                        "previous_distance": previous_dist,
                        "next_distance": next_dist,
                        "duration": -1,
                    }
                )
                if (not line.previous_geo_lat and not line.previous_geo_lng) or (
                    not line.next_geo_lat and not line.next_geo_lng
                ):
                    line.no_geolocated = True
                continue
            else:
                try:
                    osrm_url = tour_obj._osrm_get_base_url()
                    full_query = f"{osrm_url}/{line.map_tour_line_coordinates}?"
                    req = requests.get(full_query, timeout=10)
                    res = req.json()
                except Exception:
                    res = {}

            if not res or not res.get("routes"):
                raise UserWarning(_("Unexpected routing error"))

            # a leg is a route between two waypoints.
            legs = res["routes"][0]["legs"]
            if len(line.tour_id.tour_line_ids) + 1 == len(legs) - 1:  # departure -> slot -> arrival : 2 routes 1 slot
                leg = legs[line.previous_sequence]
                next_leg = legs[line.previous_sequence + 1]
                # Route : A ---> B ---> C ---> D
                # leg 0 : A ---> B, leg 1 : B ---> C, ...
                previous_distance = leg["distance"] / 1000
                previous_duration = leg["duration"] / 60
                next_distance = next_leg["distance"] / 1000
                next_duration = next_leg["duration"] / 60
                line.update(
                    {
                        "previous_distance": previous_distance,
                        "previous_duration": previous_duration,
                        "next_distance": next_distance,
                        "next_duration": next_duration,
                        "distance": previous_distance + next_distance,
                        "duration": previous_duration + next_duration,
                    }
                )
            else:
                line.no_geolocated = True


class OFTourAppointmentLineMixin(models.AbstractModel):
    _name = "of.tour.appointment.line.mixin"
    _description = "Appointment Line Mixin"

    def toggle_selected(self):
        """Helper to set a decoration style on the line that was clicked"""
        self.ensure_one()
        self.search([("wizard_id", "=", self.wizard_id.id), ("selected", "=", True)]).write({"selected": False})
        self.selected = True

    def action_button_view_tour(self):
        """Update the map on the right side of the list view. That should display the tour of the current intervenant"""
        self.ensure_one()
        self.wizard_id.map_tour_id = self.tour_id.id or False
        self.wizard_id.map_line_id = self.id
        # force the map to be recomputed
        self.wizard_id.sudo()._compute_map_data()
        self.toggle_selected()
        # update OSRM data of the tour
        self.tour_id and self.tour_id.sudo()._osrm_recompute_data_if_needed()
        # get the route between the previous/next interventions and the meet we are trying to schedule
        self.wizard_id.additional_record_geometry_data = self.wizard_id._get_additional_record_geometry_data(self)

    def action_button_confirm_slot(self):
        self.ensure_one()
        self.action_select()
        return self.wizard_id.action_button_confirm()

    def action_select(self, sudo=False):
        """Sélectionne ce créneau en tant que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        selected_line = self.search([("wizard_id", "=", self.wizard_id.id), ("selected", "=", True)])
        selected_line.write({"selected": False})
        self.selected = True

        vals = self._prepare_wizard_values(sudo)
        self.wizard_id.write(vals)

    def _prepare_wizard_values(self, sudo=False):
        if sudo:
            address = self.wizard_id.partner_address_id.sudo()
            name = address.name or (address.parent_id and address.parent_id.sudo().name) or ""
        else:
            address = self.wizard_id.partner_address_id
            name = address.name or (address.parent_id and address.parent_id.name) or ""
        name += address.zip and f" {address.zip}" or ""
        name += address.city and f" {address.city}" or ""
        # if we are on the delegated object we must use the id of the parent object
        selected_line_id = self.id
        return {
            "name": name,
            "employee_id": self.employee_id.id,
            "selected_datetime": self.start,
            "selected_line_id": selected_line_id,
            "map_line_id": selected_line_id,
            "map_tour_id": self.tour_id.id or False,
        }


class OFTourAppointmentLine(models.TransientModel):
    _name = "of.tour.appointment.line.wizard"
    _description = "Appointment Proposals"
    _inherit = ["of.tour.appointment.line.mixin"]

    available_slot_id = fields.Many2one(comodel_name="of.planning.available.slot", string="Available Slot")
    tour_id = fields.Many2one(
        comodel_name="of.planning.tour", string="Tour", related="available_slot_id.tour_id", required=True
    )
    map_tour_line_coordinates = fields.Char(
        string="Wizard Line Coordinates", compute="_compute_map_tour_line_coordinates"
    )
    date = fields.Date(related="tour_id.date", store=True)
    date_str = fields.Char(string="Date (str)", compute="_compute_date_str")
    weekday = fields.Selection(related="tour_id.weekday")
    start = fields.Datetime(related="available_slot_id.start", store=True)
    time_slot = fields.Char(related="available_slot_id.time_slot", store=True)
    employee_id = fields.Many2one(related="tour_id.employee_id", store=True)
    wizard_id = fields.Many2one(
        comodel_name="of.tour.appointment.wizard", string="Wizard", required=True, ondelete="cascade", index=True
    )
    template_id = fields.Many2one(string="Intervention Template", comodel_name="of.planning.intervention.template")
    search_mode = fields.Selection(related="wizard_id.search_mode", store=True)
    previous_sequence = fields.Integer(compute="_compute_previous_sequence")
    intervention_id = fields.Many2one(comodel_name="calendar.event", string="Intervention", index=True)

    previous_geo_lat = fields.Float(
        string="Latitude of the previous intervention", compute="_compute_previous_geo", store=True
    )
    previous_geo_lng = fields.Float(
        string="Longitude of the previous intervention", compute="_compute_previous_geo", store=True
    )
    next_geo_lat = fields.Float(string="Latitude of the next intervention", compute="_compute_next_geo", store=True)
    next_geo_lng = fields.Float(string="Longitude of the next intervention", compute="_compute_next_geo", store=True)

    distance = fields.Float(
        string="Total Distance",
        digits=(12, 0),
        help="Total distance in km. Is the sum of the previous distance and the next distance.",
    )
    previous_distance = fields.Float(digits=(12, 0), help="Previous Distance in km")
    next_distance = fields.Float(digits=(12, 0), help="Next Distance in km")

    duration = fields.Float(
        string="Total Duration",
        default=-1,
        digits=(12, 0),
        help="Total duration in minutes. Is the sum of the previous duration and the next duration.",
    )
    previous_duration = fields.Float(digits=(12, 0), help="Previous Duration in minutes")
    previous_duration_str = fields.Char(string="Previous Duration (str)", compute="_compute_previous_duration_str")
    next_duration = fields.Float(digits=(12, 0), help="Next Duration in minutes")
    next_duration_str = fields.Char(string="Next Duration (str)", compute="_compute_next_duration_str")

    useful_distance = fields.Float(
        digits=(12, 0),
        compute="_compute_useful_distance",
        store=True,
        help="Useful Distance in km",
    )
    useful_duration = fields.Float(
        digits=(12, 0), compute="_compute_useful_duration", help="Useful Duration in minutes"
    )

    best = fields.Boolean(string="Best slot")
    selected = fields.Boolean(string="Selected Slot")
    description = fields.Text(string="Description", related="wizard_id.description")
    no_geolocated = fields.Boolean()

    @api.depends("date")
    def _compute_date_str(self):
        for line in self:
            user_lang = self.env.user.lang or "en_US"
            line.date_str = format_date(line.date, format="full", locale=user_lang).capitalize() if line.date else False

    @api.depends("next_duration")
    def _compute_next_duration_str(self):
        """Compute the string of the duration to display in the kanban view (// operator doesn't work in qweb)"""
        for line in self:
            if line.next_duration:
                line.next_duration_str = (
                    f"{int(line.next_duration // 60):02d}:{int(line.next_duration % 60):02d}"  # noqa : E231
                )
            else:
                line.next_duration_str = "00:00"

    @api.depends("previous_duration")
    def _compute_previous_duration_str(self):
        """Compute the string of the duration to display in the kanban view (// operator doesn't work in qweb)"""
        for line in self:
            if line.previous_duration:
                line.previous_duration_str = (
                    f"{int(line.previous_duration // 60):02d}:{int(line.previous_duration % 60):02d}"  # noqa : E231
                )
            else:
                line.previous_duration_str = "00:00"

    @api.depends("available_slot_id", "available_slot_id.previous_tour_line_id")
    def _compute_previous_geo(self):
        """Compute the coordinates of the previous intervention"""
        for line in self:
            if previous_tour_line := line.available_slot_id.previous_tour_line_id:
                line.write(
                    {
                        "previous_geo_lat": previous_tour_line.geo_lat,
                        "previous_geo_lng": previous_tour_line.geo_lng,
                    }
                )
            else:
                line.write(
                    {
                        "previous_geo_lat": line.tour_id.start_address_id.partner_latitude,
                        "previous_geo_lng": line.tour_id.start_address_id.partner_longitude,
                    }
                )

    @api.depends("available_slot_id", "available_slot_id.next_tour_line_id")
    def _compute_next_geo(self):
        """Compute the coordinates of the next intervention"""
        for line in self:
            if next_tour_line := line.available_slot_id.next_tour_line_id:
                line.write(
                    {
                        "next_geo_lat": next_tour_line.geo_lat,
                        "next_geo_lng": next_tour_line.geo_lng,
                    }
                )
            else:
                line.write(
                    {
                        "next_geo_lat": line.tour_id.return_address_id.partner_latitude,
                        "next_geo_lng": line.tour_id.return_address_id.partner_longitude,
                    }
                )

    @api.depends("search_mode")
    def _compute_useful_distance(self):
        am_limit_float = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of.planning.tour.tour_am_limit_float", DEFAULT_AM_LIMIT_FLOAT)
        )
        for line in self:
            search_mode = line.search_mode
            if search_mode == "oneway":
                line.useful_distance = line.previous_distance
            elif search_mode == "oneway_am_return_pm":
                line.useful_distance = (
                    line.previous_distance
                    if line.available_slot_id.start.hour <= am_limit_float  # one way, if morning
                    else line.next_distance  # return, if afternoon
                )
            elif search_mode == "oneway_or_return":
                line.useful_distance = min(line.previous_distance, line.next_distance)
            elif search_mode == "return":
                line.useful_distance = line.next_distance
            elif search_mode == "round_trip":
                line.useful_distance = line.distance

    @api.depends("search_mode")
    def _compute_useful_duration(self):
        am_limit_float = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of.planning.tour.tour_am_limit_float", DEFAULT_AM_LIMIT_FLOAT)
        )
        for line in self:
            search_mode = line.search_mode
            if search_mode == "oneway":
                line.useful_duration = line.previous_duration
            elif search_mode == "oneway_am_return_pm":
                line.useful_duration = (
                    line.previous_duration
                    if line.available_slot_id.start.hour <= am_limit_float
                    else line.next_duration
                )
            elif search_mode == "oneway_or_return":
                line.useful_duration = min(line.previous_duration, line.next_duration)
            elif search_mode == "return":
                line.useful_duration = line.next_duration
            elif search_mode == "round_trip":
                line.useful_duration = line.duration

    @api.depends("available_slot_id", "available_slot_id.previous_tour_line_id")
    def _compute_previous_sequence(self):
        """
        Compute the sequence of the previous intervention.
        Used for the computation of this wizard line coordinates.
        """
        for line in self:
            line.previous_sequence = (
                line.available_slot_id.previous_tour_line_id.sequence
                if line.available_slot_id.previous_tour_line_id
                else 0
            )

    @api.depends("tour_id.map_tour_line_coordinates", "previous_sequence")
    def _compute_map_tour_line_coordinates(self):
        """Take the coordinates of the tour and insert the coordinates of the wizard"""
        for line in self:
            wizard = line.wizard_id
            geo_data = (
                line.tour_id.map_tour_line_coordinates.split(";") if line.tour_id.map_tour_line_coordinates else []
            )
            geo_data.insert(
                line.previous_sequence + 1,
                f"{round(wizard.geo_lng, 7)},{round(wizard.geo_lat, 7)}",  # noqa
            )
            line.map_tour_line_coordinates = ";".join(geo_data)
