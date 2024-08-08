# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import uuid

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class ESBBus(models.Model):
    _name = 'esb.bus'
    _rec_name = 'channel'

    channel = fields.Char()
    ttype = fields.Many2one(comodel_name='esb.type.bus', string="Type of bus")
    data = fields.Many2one(comodel_name='esb.data')
    uuid = fields.Char(default=uuid.uuid4())
    date = fields.Datetime(default=fields.Datetime.now())

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)

        for res in res_list:
            # D'abord, on ajoute l'UUID du message dans la properties de la data :
            properties = json.loads(res.data.properties)
            properties['uuid'] = res.uuid
            res.data.properties = json.dumps(properties)

            # on va chercher les règles qui sont configurées sur le channel / ttype
            rules = self.env['esb.rule'].search([('channel_bus', '=', res.channel), ('type_bus', '=', res.ttype.id)])
            for rule in rules:
                service_exec = rule.service.execute_with_delay(args=res.data)
                # on ne va logger que les services "user" qui sont lancés
                if rule.ttype == "user":
                    data_value = {
                        'in_data': json.dumps(
                            {
                                'type': 'service',
                                'id': rule.service.id,
                                'job': service_exec._uuid,
                                'name': rule.service.name,
                            }
                        ),
                        'properties': json.dumps({'uuid': res.uuid}),
                    }
                    data = self.env['esb.data'].create(data_value)
                    bus_value = {
                        'channel': 'history',
                        'ttype': self.env.ref('of_esb.type_logs').id,
                        'data': data.id,
                    }
                    self.create(bus_value)
        return res_list
