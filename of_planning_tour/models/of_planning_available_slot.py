# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from .of_planning_tour import DEFAULT_AM_LIMIT_FLOAT

SELECTION_DAY_PERIOD = [
    ("both", "Morning and Afternoon"),
    ("morning", "Morning"),
    ("afternoon", "Afternoon"),
]


class OFPlanningAvailableSlot(models.Model):
    _name = "of.planning.available.slot"
    _description = "Available slot on planning"
    _order = "start"

    active = fields.Boolean(default=True)
    name = fields.Char()
    time_slot = fields.Char(compute="_compute_time_slot", store=True)

    tour_id = fields.Many2one(comodel_name="of.planning.tour", string="Tour", required=True, ondelete="cascade")
    previous_tour_line_id = fields.Many2one(
        comodel_name="of.planning.tour.line", string="Previous Tour Line", compute="_compute_previous_tour_line_id"
    )
    next_tour_line_id = fields.Many2one(
        comodel_name="of.planning.tour.line", string="Next Tour Line", compute="_compute_next_tour_line_id"
    )

    employee_id = fields.Many2one(comodel_name="hr.employee", related="tour_id.employee_id", store=True)

    date = fields.Date(related="tour_id.date", store=True)
    weekday = fields.Selection(related="tour_id.weekday")
    dayofweek = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Day of Week",
        compute="_compute_dayofweek",
    )
    start = fields.Datetime(readonly=False, required=True)
    stop = fields.Datetime(readonly=False, required=True)
    duration = fields.Float(compute="_compute_duration", help="Available duration (expressed in hour)", store=True)
    day_period = fields.Selection(selection=SELECTION_DAY_PERIOD, compute="_compute_day_period", store=True)

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("date")
    def _compute_dayofweek(self):
        for record in self:
            record.dayofweek = str(record.date.weekday()) if record.date else False

    @api.depends("start")
    def _compute_day_period(self):
        am_limit_float = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of.planning.tour.tour_am_limit_float", DEFAULT_AM_LIMIT_FLOAT)
        )
        for record in self:
            if fields.Datetime.context_timestamp(self, record.start).hour < am_limit_float:
                record.day_period = "morning"
            else:
                record.day_period = "afternoon"

    @api.depends("tour_id.tour_line_ids")
    def _compute_previous_tour_line_id(self):
        for record in self:
            if lines := record.mapped("tour_id.tour_line_ids").filtered(lambda li: li.date_start < record.start):
                record.previous_tour_line_id = lines[-1]
            else:
                record.previous_tour_line_id = False

    @api.depends("tour_id.tour_line_ids")
    def _compute_next_tour_line_id(self):
        for record in self:
            if lines := record.mapped("tour_id.tour_line_ids").filtered(lambda li: li.date_start >= record.stop):
                record.next_tour_line_id = lines[0]
            else:
                record.next_tour_line_id = False

    @api.depends("start", "stop")
    def _compute_duration(self):
        for record in self:
            if record.start and record.stop:
                record.duration = round(((record.stop - record.start).total_seconds() / 3600.0), 2)
            else:
                record.duration = False

    @api.depends("start", "stop")
    def _compute_time_slot(self):
        for record in self:
            calendar_tz_name = (
                record.employee_id.resource_calendar_id.tz
                if record.employee_id.resource_calendar_id
                else "Europe/Paris"
            )
            record = record.with_context(tz=calendar_tz_name)
            if record.start and record.stop:
                start_str = fields.Datetime.context_timestamp(record, record.start).strftime("%H:%M")
                stop_str = fields.Datetime.context_timestamp(record, record.stop).strftime("%H:%M")
                record.time_slot = " - ".join([start_str, stop_str])
            else:
                record.time_slot = False

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    def name_get(self):
        return [(record.id, f"{record.tour_id.name}{f' - {record.time_slot}' or ''}") for record in self]

    # --------------------------------------------------------------------------
    # Action methods
    # --------------------------------------------------------------------------

    def action_button_toggle_active(self):
        for record in self:
            record.active = not record.active

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def cron_archive_past_available_slots(self):
        self.search([("stop", "<", datetime.now())]).write({"active": False})

    def cron_clean_archived_available_slots(self):
        self.search([("stop", "<", datetime.now() - relativedelta(days=14))]).unlink()
