# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = 'crm.lead'

    # Partner related fields
    of_website = fields.Char(related='partner_id.website')
    tag_ids = fields.Many2many(
        comodel_name='res.partner.category',
        related='partner_id.category_id',
        string='Tags',
        help="Classify and analyze your lead/opportunity categories like: Training, Service",
    )
    meeting_ids = fields.Many2many(comodel_name='calendar.event', string="Meetings", related='partner_id.meeting_ids')
    # Partner fields
    is_company = fields.Boolean(string="Is a company")
    zip_id = fields.Many2one(comodel_name='res.city.zip', string="City/Location")

    # Custom CRM fields
    of_ref = fields.Char(string="Reference", copy=False)
    of_canvasser_id = fields.Many2one(comodel_name='res.users', string="Canvasser")
    of_prospecting_date = fields.Date(string="Prospecting date", default=fields.Date.today)
    of_closing_date = fields.Date(string="Closing date")
    of_additionnal_infos = fields.Html(string="Additionnal informations")
    of_referred_id = fields.Many2one(comodel_name='res.partner', string="Brought by", help="Name of business referrer")
    description = fields.Html(string="Follow-up")
    report_description = fields.Html(string="Second follow-up")
    of_color_ft = fields.Char(string="Font color")
    of_color_bg = fields.Char(string="Background color")

    # Map view fields
    of_next_activity_name = fields.Char(string="Next activity name")
    of_color_map = fields.Char(string="Marker color")

    # Activities
    of_activity_ids = fields.One2many(
        comodel_name='of.crm.activity',
        inverse_name='opportunity_id',
        string="Activities",
        context={'active_test': False},
    )
    of_next_action_activity_id = fields.Many2one(
        comodel_name='of.crm.activity',
        string="Activity requiring next action",
    )

    of_date_action = fields.Datetime(  # store=True car of_date_action est la date de référence pour la vue calendar
        string="Date of next action"
    )
    of_date_action_filter = fields.Date(
        string="Date of next action",
        store=True,
        index=True,
        help="Technical field used in the search view to filter on the date of the next action",
    )
    of_title_action = fields.Char(string="Name of next action")

    # Reporting fields
    of_my_company = fields.Boolean(
        string="Is my store ?", compute='_compute_is_my_company', search='_search_is_my_company'
    )

    def action_button_new_activity(self):
        self.ensure_one()
        return self.env.ref('of_crm.of_crm_activity_schedule_action').read()[0]
