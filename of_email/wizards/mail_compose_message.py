# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    of_reply_to = fields.Char(
        string="Reply-To",
        help="Custom Reply-To email address to use for the message. This field has priority over the default Reply-To ",
    )

    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        values = super()._onchange_template_id(template_id, composition_mode, model, res_id)
        if composition_mode != "mass_mail" and template_id:
            template = self.env["mail.template"].browse(template_id)
            if template.of_reply_to:
                if of_reply_to := template._render_field("of_reply_to", [res_id]):
                    of_reply_to = of_reply_to[res_id]
                    values["value"]["of_reply_to"] = of_reply_to
        return values

    def get_mail_values(self, res_ids):
        results = super().get_mail_values(res_ids)
        if self.composition_mode != "mass_mail" and self.template_id and self.template_id.of_reply_to:
            for res_id in res_ids:
                results[res_id]["reply_to"] = self.of_reply_to
        return results
