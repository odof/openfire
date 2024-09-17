# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import uuid

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class ESBBus(models.Model):
    _name = 'of.esb.bus'
    _rec_name = 'channel'

    channel = fields.Char()
    ttype = fields.Many2one(comodel_name='of.esb.type.bus', string="Type of bus")
    data = fields.Many2one(comodel_name='of.esb.data')
    uuid = fields.Char(default=lambda r: uuid.uuid4())
    date = fields.Datetime(default=fields.Datetime.now)

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)

        for res in res_list:
            # on va chercher les règles qui sont configurées sur le channel / ttype
            rules = self.env['of.esb.rule'].search(
                [('channel_bus', 'in', [res.channel, False]), ('type_bus', '=', res.ttype.id)]
            )
            for rule in rules:
                service_exec = rule.service.execute_with_delay(args=res.data)
                data = {
                    'type': 'service',
                    'id': rule.service.id,
                    'job': service_exec._uuid,
                    'name': rule.service.name,
                    'uuid': res.uuid,
                }
                properties = {'uuid': res.uuid}

                self.send_bus(
                    ttype=self.env.ref('of_esb.type_logs'), channel='history', data=data, properties=properties
                )

        return res_list

    @api.model
    def send_bus(self, ttype, channel, data, properties=None):
        # ttype : contient le nom du type de bus
        # channel : le nom du channel
        # data : dictionnaire contenant deux clefs uuid et in_data
        #   uuid est l'uuid du trigger en cours d'exécution
        #   in_data c'est la donnée à envoyer dans le bus
        logger.info(f"send_bus: {ttype.name},{channel},{data},{properties}")

        if not properties:
            properties = {}
        value_data = {
            'in_data': json.dumps(data),
            'properties': json.dumps(properties),
        }
        if data.get('uuid'):
            value_data['properties'] = json.dumps(dict({'uuid': data['uuid']}))

        res_data = self.env['of.esb.data'].create(value_data)

        value_bus = {'channel': channel, 'ttype': ttype.id, 'data': res_data.id, 'uuid': data.get('uuid')}
        bus = self.create(value_bus)
        return bus
