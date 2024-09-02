# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, fields, models

logger = logging.getLogger(__name__)


class ESBConnection(models.Model):
    _name = 'of.esb.connection'

    name = fields.Char()
    ttype = fields.Selection([], string="Type")
    security = fields.Many2one(comodel_name='of.esb.security', string="Security")
    is_valid = fields.Boolean()

    def connect(self):
        if hasattr(self, f'connect_{self.ttype}'):
            return getattr(self, f'connect_{self.ttype}')()

        return False

    def get_out_example(self):
        pass

    def get_in_example(self):
        pass

    def test_connection(self):
        res = self.connect()
        if res:
            message = _("Connection Test Successful!")
            self.is_valid = True
            logger.info(message)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                },
            }
        else:
            message = _("Connection Test Unsuccessful!")
            self.is_valid = False
            logger.info(message)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'error',
                    'sticky': False,
                },
            }
