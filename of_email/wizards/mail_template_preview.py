# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import UserError


class MailTemplatePreview(models.TransientModel):
    _inherit = "mail.template.preview"

    @api.depends("lang", "resource_ref")
    def _compute_mail_template_fields(self):
        """Override to add 'of_reply_to' to the fields to be computed."""
        copy_depends_values = {"lang": self.lang}
        mail_template = self.mail_template_id.with_context(lang=self.lang)
        try:
            if not self.resource_ref:
                self._set_mail_attributes()
            else:
                copy_depends_values["resource_ref"] = f"{self.resource_ref._name},{self.resource_ref.id}"  # noqa
                mail_values = mail_template.with_context(template_preview_lang=self.lang).generate_email(
                    self.resource_ref.id, self._MAIL_TEMPLATE_FIELDS + ["partner_to", "of_reply_to"]
                )
                if mail_template.of_reply_to and mail_values.get("of_reply_to") and not mail_values.get("reply_to"):
                    mail_values["reply_to"] = mail_values.get("of_reply_to")
                self._set_mail_attributes(values=mail_values)
            self.error_msg = False
        except UserError as user_error:
            self._set_mail_attributes()
            self.error_msg = user_error.args[0]
        finally:
            # Avoid to be change by a cache invalidation (in generate_mail), e.g. Quotation / Order report
            for key, value in copy_depends_values.items():
                self[key] = value
