# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class SendSMS(models.TransientModel):
    _inherit = 'sms.composer'

    of_sender_id = fields.Many2one(comodel_name='of.sms.sender', string="Sender")
    of_is_commercial = fields.Boolean(string='Is Commercial')
    of_send_date = fields.Date(string="Date to send")

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        model = result.get('res_model')

        if model and not result.get('of_sender_id'):
            if ir_model := self.env['ir.model'].search([('model', '=', model)], limit=1):
                sender = self.env['of.sms.sender'].search([('model', '=', ir_model.id)], limit=1)
            else:
                sender = self.env['of.sms.sender'].search([('model', '=', '')], limit=1)
            result['of_sender_id'] = sender.id

        if model == 'res.partner':
            if numbers := self.env['res.partner'].browse(result.get('res_id')).get_mobile_numbers():
                composition_mode = result.get('composition_mode')
                if composition_mode == 'comment':
                    result['recipient_single_number_itf'] = numbers[0]
                else:
                    result['numbers'] = ','.join(numbers)

        return result

    def _action_send_sms_comment(self, records=None):
        kwargs = {
            'of_sender_id': self.of_sender_id.id,
            'of_is_commercial': self.of_is_commercial,
            'of_send_date': self.of_send_date,
        }
        records = records if records is not None else self._get_records()
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')

        messages = self.env['mail.message']
        all_bodies = self._prepare_body_values(records)

        for record in records:
            messages += record._message_sms(
                all_bodies[record.id],
                subtype_id=subtype_id,
                number_field=self.number_field_name,
                sms_numbers=self.sanitized_numbers.split(',') if self.sanitized_numbers else None,
                **kwargs,
            )
        return messages

    def _prepare_mass_sms_values(self, records):
        results = super()._prepare_mass_sms_values(records)
        for record in results:
            record = dict(
                record,
                of_sender_id=self.of_sender_id.id,
                of_is_commercial=self.of_is_commercial,
                of_date_to_send=self.of_send_date,
            )
        return results

    def _action_send_sms_numbers(self):
        """Send the SMS to the numbers.
        TODO: OVH does not allow batch sending here, so we send one by one.
        """
        for number in self.sanitized_numbers.split(','):
            sms = self.env['sms.sms'].create(
                {
                    'of_sender_id': self.of_sender_id.id,
                    'of_date_to_send': self.of_send_date,
                    'of_is_commercial': self.of_is_commercial,
                    'body': self.body,
                    'number': number,
                }
            )
            self.env['sms.api']._send_sms_with_ovh_http(number, self.body, sms.id)
        return True
