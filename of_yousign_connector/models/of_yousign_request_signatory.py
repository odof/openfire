# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.of_base.models.res_partner import convert_phone_number


class YousignRequestSignatory(models.Model):
    _name = "of.yousign.request.signatory"
    _order = "request_id, sequence"
    _rec_name = "partner_id"

    request_id = fields.Many2one(
        comodel_name="yousign.request",
        string="Request",
        ondelete="cascade",
    )
    sequence = fields.Integer()
    partner_id = fields.Many2one(comodel_name="res.partner", ondelete="restrict")
    firstname = fields.Char()
    lastname = fields.Char()
    email = fields.Char(string="E-mail")
    mobile = fields.Char()
    auth_mode = fields.Selection(
        selection=[
            ("sms", "SMS"),
            ("email", "E-Mail"),
        ],
        default="sms",
        string="Authentication Mode",
        required=True,
        help="Authentication mode used for the signer",
    )
    top_mention = fields.Char()
    bottom_mention = fields.Char()
    ys_identifier = fields.Char(string="Yousign ID", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("signed", "Signed"),
            ("refused", "Refused"),
        ],
        string="Signature State",
        readonly=True,
        default="draft",
    )
    comment = fields.Text()
    signature_date = fields.Date(readonly=True)
    signature_link = fields.Char()
    signature_link_expiration = fields.Datetime(
        string="Expiration date for signature link",
    )

    def create(self, vals):
        mobile = vals.get("mobile", False)
        partner_id = vals.get("partner_id", False)
        if mobile and partner_id:
            partner = self.env["res.partner"].browse(partner_id)
            country_code = partner.country_id.code and partner.country_id.code.upper()
            converted_phone_number = convert_phone_number(mobile, country_code)
            vals["mobile"] = converted_phone_number
        return super(YousignRequestSignatory, self).create(vals)

    def write(self, vals):
        mobile = vals.get("mobile", False)
        partner_id = vals.get("partner_id", False)
        if mobile or partner_id:
            res = False
            for record in self:
                record_vals = vals.copy()
                mobile = vals.get("mobile", record.mobile)
                partner_id = vals.get("partner_id", record.partner_id.id)
                if mobile and partner_id:
                    partner = self.env["res.partner"].browse(partner_id)
                    country_code = (
                        partner.country_id.code and partner.country_id.code.upper()
                    )
                    converted_phone_number = convert_phone_number(mobile, country_code)
                    record_vals["mobile"] = converted_phone_number
                res = super(YousignRequestSignatory, record).write(record_vals)
            return res
        else:
            return super(YousignRequestSignatory, self).write(vals)

    def unlink(self):
        if any(
            [
                state in ["pending", "signed", "refused"]
                for state in self.mapped("state")
            ]
        ):
            raise UserError(
                "Impossible to delete a signatory in the state pending, signed or refused."
            )
        return super(YousignRequestSignatory, self).unlink()

    @api.depends("partner_id")
    def _compute_partner_data(self):
        if self.partner_id:
            self.email = self.partner_id.email or False
            self.mobile = self.partner_id.mobile
            if hasattr(self.partner_id, "firstname") and not self.partner_id.is_company:
                self.firstname = self.partner_id.firstname
                self.lastname = self.partner_id.lastname
            else:
                self.firstname = False
                self.lastname = self.partner_id.name
