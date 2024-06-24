# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class ESBService(models.Model):
    _name = 'esb.service'

    name = fields.Char()
    code = fields.Text()
    exec_active = fields.Boolean(string="Active", default=True)

    def execute_with_delay(self, args={}):
        if self.exec_active:
            return self.with_delay().execute(args)
        else:
            return {'error': 'this service is not active'}

    def execute(self, args={}):
        if self.code and self.exec_active:
            exec(self.code, {'args': args, 'self': self})
            return args
        elif not self.exec_active:
            return {'error': 'this is not active'}
        else:
            return {'error': 'Code is empty'}
