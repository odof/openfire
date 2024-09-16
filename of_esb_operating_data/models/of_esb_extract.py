# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import uuid

from odoo import fields, models


class ESBExtract(models.Model):
    _name = 'of.esb.extract'

    name = fields.Char('Name')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    lines = fields.One2many(comodel_name='of.esb.extract.line', inverse_name='extract_id', string='Lines')
    uuid = fields.Char(default=lambda r: uuid.uuid4())

    def execute(self, args):
        for record in self:
            properties = json.loads(args.properties)

            for line in record.lines:
                in_data = [
                    {
                        'connection': line.connection_id.name,
                        'data': json.loads(line.data),
                        'bus_type': self.env.ref("of_esb_operating_data.type_transform").name,
                        'bus_channel': line.transform_id.name,
                    }
                ]

                data = {'data': in_data, 'type': line.connection_id.ttype, 'uuid': properties.get('uuid')}
                self.env['of.esb.bus'].send_bus('Internal', 'get_data', data)
