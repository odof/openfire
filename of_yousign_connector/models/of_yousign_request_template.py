# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFYousignRequestTemplate(models.Model):
    _name = "of.yousign.request.template"
    _description = "YouSign Request Template"
    _order = "name"

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        comodel_name="ir.model", string="Applies to", required=True, ondelete="cascade"
    )
    model = fields.Char(related="model_id.model", readonly=True, store=True)
    lang = fields.Char(string="Language")
    ordered = fields.Boolean(string="Sign one after the other")
    init_mail_subject = fields.Char()
    init_mail_body = fields.Text()
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
    report_ids = fields.Many2many(
        comodel_name="ir.actions.report", string="Default Report to Sign"
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", ondelete="cascade"
    )
    signatory_ids = fields.One2many(
        comodel_name="of.yousign.request.template.signatory",
        inverse_name="template_id",
        string="Signatories",
    )
    # experience_id = fields.Many2one(
    #     comodel_name="of.yousign.experience", string="Expérience"
    # )
    creator = fields.Boolean(string="Notify the creator")
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="of_yousign_request_template_res_partner_rel",
        column1="template_request_id",
        column2="partner_id",
        string="Partners to notify",
        domain=[("email", "!=", False)],
    )

    def prepare_template2request(self):
        self.ensure_one()
        res = {
            "ordered": self.ordered,
            "has_automatic_reminder": self.has_automatic_reminder,
            "remind_interval": self.remind_interval,
            "remind_limit": self.remind_limit,
            # "of_experience_id": self.of_experience_id.id or False,
        }
        return res
