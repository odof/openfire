# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    # Store True pour éviter le recalcul lors de l'appui sur n'importe quel bouton.
    of_computed_body = fields.Html(
        string="Computed body", compute="_compute_of_computed_body", sanitize_style=True, strip_classes=True, store=True
    )

    # Calcul des champs dans mail, mail_compose_message.py : render_message()
    @api.depends("res_id", "body")
    def _compute_of_computed_body(self):
        for composer in self:
            if not composer.res_id:
                composer.of_computed_body = False
                continue
            composer.of_computed_body = composer.render_message([composer.res_id])[composer.res_id]["body"]

    def button_reload_computed_body(self):
        self._compute_of_computed_body()
        return {"type": "ir.actions.do_nothing"}

    # Permet à l'auteur du mail de le recevoir en copie si le paramètre du modèle est vrai.
    def action_send_mail(self):
        return super(
            MailComposer, self.with_context(mail_notify_author=self.template_id and self.template_id.of_copy_to_sender)
        ).action_send_mail()
