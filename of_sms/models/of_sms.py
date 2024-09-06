# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import UserError


class OFSMS(models.AbstractModel):
    _name = 'of.sms'

    @api.model
    def action_send_sms(self, res_id, model, partner_id):
        ir_model = self.env['ir.model'].search([('model', '=', model)], limit=1)
        if ir_model:
            sender = self.env['of.sms.sender'].search([('model', '=', ir_model.id)], limit=1)
        if not sender:
            sender = self.env['of.sms.sender'].search([('model', '=', False)], limit=1)

        if not sender:
            raise UserError("Error ! (#ED100)\n\nNo sender(s) found. Please configure it.")

        if partner_id:
            mobile_numbers = partner_id.get_mobile_numbers()
            if mobile_numbers:
                return {
                    'name': u'Compose SMS',
                    'view_mode': 'form',
                    'res_model': 'sms.composer',
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {
                        'default_of_sender_id': sender.id,
                        'default_recipient_single_number_itf': mobile_numbers[0],
                        'default_res_id': res_id,
                        'default_res_model': model,
                        'default_composition_mode': 'comment',
                    },
                }
        # Si on arrive ici, c'est que l'on n'a pas de numéro de mobile à qui envoyer le SMS
        raise UserError("This customer has no valid mobile number!")
