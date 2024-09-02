# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import json
import logging
import uuid

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class ESBLoad(models.Model):
    _name = 'of.esb.load'

    name = fields.Char('Name')
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    connection_id = fields.Many2one(comodel_name='of.esb.connection', string="Connection")
    uuid = fields.Char(default=lambda r: uuid.uuid4())

    def execute(self, args):
        for record in self:
            properties = json.loads(args.properties)
            data = json.loads(args.in_data)

            in_data = [
                {
                    'connection': record.connection_id.name,
                    'data': data.get('data', {}),
                }
            ]

            bus_data = {'data': in_data, 'type': record.connection_id.ttype, 'uuid': properties.get('uuid')}

            self.env['of.esb.bus'].send_bus('Internal', 'set_data', bus_data)
