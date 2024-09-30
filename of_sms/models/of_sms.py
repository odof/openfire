# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class OFSMS(models.AbstractModel):
    """Abstract model to send SMS"""

    _name = "of.sms"
    _description = "OF SMS"

    @api.model
    def action_send_sms(self, res_id, model, partner_id):
        if ir_model := self.env["ir.model"].search([("model", "=", model)], limit=1):
            sender = self.env["of.sms.sender"].search([("model", "=", ir_model.id)], limit=1)
        if not sender:
            sender = self.env["of.sms.sender"].search([("model", "=", False)], limit=1)

        if not sender:
            raise UserError(_("Error ! (#ED100)\n\nNo sender(s) found. Please configure it."))

        if not partner_id or not (mobile_numbers := partner_id.get_mobile_numbers()):
            # Here, we don't have any mobile number to send the SMS to, so we raise an error
            raise UserError(_("This customer has no valid mobile number!"))

        return {
            "name": _("Compose SMS"),
            "view_mode": "form",
            "res_model": "sms.composer",
            "target": "new",
            "type": "ir.actions.act_window",
            "context": {
                "default_of_sender_id": sender.id,
                "default_recipient_single_number_itf": mobile_numbers[0],
                "default_res_id": res_id,
                "default_res_model": model,
                "default_composition_mode": "comment",
            },
        }
