# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    logger.debug("Cannot import requests")


def rank2position_builder(width, height, x, y, mention=""):
    base = {
        "width": width,
        "height": height,
        "x": x,
        "y": y,
    }
    if mention:
        base.update(
            {
                "type": "mention",
                "mention": mention,
            }
        )
    else:
        base.update(
            {
                "type": "signature",
            }
        )
    return base


class OFYousignRequest(models.Model):
    _name = "of.yousign.request"
    _description = "Yousign Request"
    _order = "id desc"
    _inherit = ["mail.thread"]

    @api.model
    def _lang_get(self):
        langs = self.env["res.lang"].search([])
        return [(lang.code, lang.name) for lang in langs]

    name = fields.Char()
    res_name = fields.Char(
        compute="_compute_res_name",
        string="Related Document Name",
        store=True,
        readonly=True,
    )
    model = fields.Char(
        string="Related Document Model",
        select=True,
        readonly=True,
        track_visibility="onchange",
    )
    res_id = fields.Integer(
        string="Related Document ID",
        select=True,
        readonly=True,
        track_visibility="onchange",
    )
    ordered = fields.Boolean(string="Sign one after the other")
    language = fields.Selection(
        selection=lambda s: s._lang_get(),
        string="Language",
        readonly=True,
        states={"draft": [("readonly", False)]},
        track_visibility="onchange",
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Documents to Sign",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    signed_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="yousign_request_signed_attachment_rel",
        column1="request_id",
        column2="attachment_id",
        string="Signed Documents",
        readonly=True,
    )
    signatory_ids = fields.One2many(
        comodel_name="of.yousign.request.signatory",
        inverse_name="request_id",
        string="Signatories",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("signed", "Signed"),
            ("error", "Error"),
            ("archived", "Archived"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        readonly=True,
        track_visibility="onchange",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="cascade",
        readonly=True,
        states={"draft": [("readonly", False)]},
        track_visibility="onchange",
        default=lambda self: self.env["res.company"]._company_default_get(
            "yousign.request"
        ),
    )
    ys_identifier = fields.Char(
        string="Yousign ID", readonly=True, track_visibility="onchange"
    )
    last_status_update = fields.Datetime(string="Last Status Update", readonly=True)
    has_automatic_reminder = fields.Boolean(
        string="Automatic Reminder",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    remind_mail_subject = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    remind_mail_body = fields.Html(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    remind_interval = fields.Integer(
        default=3,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Number of days between 2 auto-reminders by email.",
    )
    remind_limit = fields.Integer(
        default=10,
        readonly=True,
        states={
            "draft": [("readonly", False)],
        },
    )
    expiry_date = fields.Date()
    # template_id = fields.Many2one(
    #     comodel_name="yousign.request.template",
    #     string="Template",
    #     readonly=True,
    #     states={"draft": [("readonly", False)]},
    # )
    # experience_id = fields.Many2one(
    #     comodel_name="of.yousign.experience", string="Experience"
    # )

    @api.depends("model", "res_id")
    def _compute_res_name(self):
        for req in self:
            name = "None"
            if req.res_id and req.model:
                obj = self.env[req.model].browse(req.res_id)
                name = obj.display_name
            req.res_name = name
