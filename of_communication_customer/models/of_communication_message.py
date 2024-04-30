# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfCommunicationCustomer(models.Model):
    _name = "of.communication.customer"
    _inherit = "of.communication"

    active = fields.Boolean(string="Archived", default=True, readonly=True)

    @api.model
    def _cron_communication_message_between_customer_and_base(self):
        published_messages = self.env['of.communication'].search([('state', '=', 'published')])

        for message in published_messages:
            existing_message = self.env['of.communication.customer'].search([('id', '=', message.id)])

            if not existing_message:
                self.create(
                    {
                        'name': message.name,
                        'date': message.date,
                        'type': message.type,
                        'summary': message.summary,
                        'message': message.message,
                        'start_scheduled_publication': message.start_scheduled_publication,
                        'end_scheduled_publication': message.end_scheduled_publication,
                    }
                )
            else:
                existing_message.write(
                    {
                        'date': message.date,
                        'type': message.type,
                        'summary': message.summary,
                        'message': message.message,
                        'start_scheduled_publication': message.start_scheduled_publication,
                        'end_scheduled_publication': message.end_scheduled_publication,
                    }
                )
