# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class OFYousignRequestTemplateSignatory(models.Model):
    _name = "of.yousign.request.template.signatory"
    _inherit = "mail.render.mixin"
    _description = "Signatories of Yousign Request Template"
    _order = "template_id, sequence"

    template_id = fields.Many2one(
        comodel_name="of.yousign.request.template",
        string="Template",
        ondelete="cascade",
    )
    sequence = fields.Integer()
    partner_type = fields.Selection(
        selection=[
            ("static", "Static"),
            ("dynamic", "Dynamic"),
        ],
        string="Partner Type",
        default="dynamic",
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Fixed Partner", ondelete="restrict"
    )
    partner_tmpl = fields.Char(string="Dynamic Partner")
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

    @api.depends("template_id", "template_id.model")
    def _compute_render_model(self):
        for record in self:
            record.render_model = record.template_id.model

    @api.onchange("partner_type")
    def partner_type_change(self):
        if self.partner_type == "static":
            self.partner_tmpl = False
        elif self.partner_type == "dynamic":
            self.partner_id = False

    @api.constrains("partner_type", "partner_id", "partner_tmpl")
    def check_signatory_template(self):
        for signatory in self:
            if signatory.partner_type == "static" and not signatory.partner_id:
                raise ValidationError(
                    _(
                        "Fixed Partner is required when Partner Type is set "
                        "to 'Static'"
                    )
                )
            elif signatory.partner_type == "dynamic" and not signatory.partner_tmpl:
                raise ValidationError(
                    _(
                        "Dynamic Partner is required when Partner Type is set "
                        "to 'Dynamic'"
                    )
                )

    def prepare_template2request(self, res_id):
        self.ensure_one()
        if self.partner_type == "static":
            partner = self.partner_id
        elif self.partner_type == "dynamic":
            dynamic_partner_str = self._render_field("partner_tmpl", [res_id])[res_id]
            partner = self.env["res.partner"].browse(int(dynamic_partner_str))
        else:
            raise UserError(_("Unsupported partner type"))
        vals = {
            "partner_id": partner.id,
            "email": partner.email,
            "lastname": partner.name,
            "mobile": partner.mobile,
            "auth_mode": self.auth_mode,
            "top_mention": self.top_mention,
            "bottom_mention": self.bottom_mention,
        }
        if hasattr(partner, "firstname") and not partner.is_company:
            vals.update(
                {
                    "firstname": partner.firstname,
                    "lastname": partner.lastname,
                }
            )
        return vals
