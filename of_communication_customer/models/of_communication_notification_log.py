# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfCommunicationNotificationLog(models.Model):
    """
    Class Model qui permet de récupérer les log de fermeture ou de vue d'une notification
    """

    _name = 'of.communication.notification.log'
    _description = 'Notification log'

    user_id = fields.Many2one('res.users', string="User")
    message_id = fields.Many2one('of.communication', string="Message")
    action_type = fields.Selection([('view', "View"), ('close', "Close")], string='Action Type')
    timestamp = fields.Datetime(string="Timestamp", default=fields.Datetime.now)
    read = fields.Boolean(string='Read', default=False)

    @api.model
    def mark_msg_as_read(self, message_id=False, action_type='close'):
        """
        Fonction qui permet de vérifier si les notifications d'un user on été lue
        """
        user_id = self.env.user.id

        log_entry = self.search([('user_id', '=', user_id), ('message_id', '=', message_id)], limit=1)

        if log_entry:
            log_entry.write({'read': True, 'action_type': action_type})
        else:
            self.create(
                {
                    'user_id': user_id,
                    'message_id': message_id,
                    'action_type': action_type,
                    'read': True,
                }
            )
