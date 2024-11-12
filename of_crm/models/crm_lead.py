# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.of_geolocalize.models.res_partner import GEOCODING_STATE, OPENSTREETMAP_PRECISION


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = "crm.lead"

    # Partner related fields
    of_title = fields.Many2one(related="partner_id.title", readonly=False, string="Partner Title")
    is_company = fields.Boolean(string="Is a company", tracking=True, related="partner_id.is_company", readonly=False)
    of_website = fields.Char(related="partner_id.website")
    of_partner_category_ids = fields.Many2many(
        comodel_name="res.partner.category",
        related="partner_id.category_id",
        string="Customer tags",
    )
    meeting_ids = fields.Many2many(
        comodel_name="calendar.event", string="Meetings (Partner)", related="partner_id.meeting_ids"
    )

    # Partner fields
    zip_id = fields.Many2one(comodel_name="res.city.zip", string="City/Location")

    # Custom CRM fields
    of_ref = fields.Char(string="Reference", copy=False)
    of_canvasser_id = fields.Many2one(comodel_name="res.users", string="Canvasser", tracking=True)
    of_prospecting_date = fields.Date(string="Prospecting date", default=fields.Date.today)
    of_closing_date = fields.Date(string="Closing date", tracking=True)
    of_additionnal_infos = fields.Html(string="Additionnal informations")
    of_referred_id = fields.Many2one(comodel_name="res.partner", string="Brought by", help="Name of business referrer")
    description = fields.Html(string="Follow-up")
    report_description = fields.Html(string="Second follow-up")
    of_color_ft = fields.Char(string="Font color")
    of_color_bg = fields.Char(string="Background color")

    # Map view fields
    of_phone_number_ids = fields.One2many(related="partner_id.of_phone_number_ids")
    of_next_activity_name = fields.Char(string="Next activity name")
    of_color_map = fields.Char(string="Marker color")
    of_date_action = fields.Datetime(  # store=True car of_date_action est la date de référence pour la vue calendar
        string="Date of next action"
    )
    of_date_action_filter = fields.Date(
        string="Date of next action (filter)",
        store=True,
        index=True,
        help="Technical field used in the search view to filter on the date of the next action",
    )
    of_title_action = fields.Char(string="Name of next action")
    of_partner_name = fields.Char(string="Name", compute="_compute_geocoding_data", store=True)
    of_city = fields.Char(string="City (map)", compute="_compute_geocoding_data", store=True)
    of_zip = fields.Char(string="Zip (map)", compute="_compute_geocoding_data", store=True)
    of_precision = fields.Selection(
        OPENSTREETMAP_PRECISION, compute="_compute_geocoding_data", string="Precision", store=True
    )
    of_partner_latitude = fields.Float(string="Latitude", compute="_compute_geocoding_data", store=True)
    of_partner_longitude = fields.Float(string="Longitude", compute="_compute_geocoding_data", store=True)
    of_geocoding_state = fields.Selection(
        GEOCODING_STATE,
        default="not_tried",
        help="State of geocoding",
        compute="_compute_geocoding_data",
        store=True,
    )

    # Reporting fields
    of_my_company = fields.Boolean(
        string="Is my store ?", compute="_compute_is_my_company", search="_search_is_my_company"
    )

    # ---------------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------------

    @api.depends(
        "partner_id",
        "partner_id.of_precision",
        "partner_id.partner_latitude",
        "partner_id.partner_longitude",
        "partner_id.of_geocoding_state",
    )
    def _compute_geocoding_data(self):
        for lead in self:
            if lead.partner_id:
                lead.of_partner_name = lead.partner_id.name
                lead.of_precision = lead.partner_id.of_precision
                lead.of_partner_latitude = lead.partner_id.partner_latitude
                lead.of_partner_longitude = lead.partner_id.partner_longitude
                lead.of_geocoding_state = lead.partner_id.of_geocoding_state
                lead.of_zip = lead.partner_id.zip
                lead.of_city = lead.partner_id.city

    # ---------------------------------------------------------------------
    # Action methods
    # ---------------------------------------------------------------------

    def action_schedule_meeting(self, smart_calendar=True):
        self.ensure_one()
        action = super().action_schedule_meeting()
        action["context"]["default_of_type"] = "event"
        return action
