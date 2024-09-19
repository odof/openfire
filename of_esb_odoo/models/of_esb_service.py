# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, models

logger = logging.getLogger(__name__)


class ESBService(models.Model):
    _inherit = 'of.esb.service'

    def get_data_odoo(self, args):
        datas = json.loads(args.in_data)['data']
        uuid = json.loads(args.in_data)['uuid']
        for data in datas:
            bus_type = data['bus_type']
            bus_channel = data['bus_channel']
            connection = self.env['of.esb.connection'].search([('id', '=', data['connection_id'])], limit=1)
            if connection:
                odoo_base = connection.connect()
                lines = data['data']
                logger.info(lines)
                for line in lines:
                    logger.info(line)
                    obj = odoo_base.env[line['model']]
                    if connection.odoo_company_id:
                        obj = obj.with_context(allowed_company_ids=[connection.odoo_company_id])
                    line['result'] = obj.search_read(
                        domain=line.get('domain', []),
                        offset=line.get('offset', 0),
                        limit=line.get('limit', 0),
                        fields=line['fields'],
                    )
                data['uuid'] = uuid

                ttype = self.env['of.esb.type.bus'].search([('name', '=', bus_type)], limit=1)

                self.env['of.esb.bus'].send_bus(ttype=ttype, channel=bus_channel, data=data, properties={'uuid': uuid})
        return []

    def set_data_odoo(self, args):
        datas = json.loads(args.in_data)['data']
        for data in datas:
            connection = self.env['of.esb.connection'].search([('id', '=', data['connection_id'])], limit=1)
            if connection:
                odoo_base = connection.connect()
                lines = data['data']
                for line in lines:
                    obj = odoo_base.env[line['model']]
                    if connection.odoo_company_id:
                        obj = obj.with_context(allowed_company_ids=[connection.odoo_company_id])
                    results = line['result']
                    for result in results:
                        if res_id := result.get('id'):
                            # on est sur une mise à jour
                            record = obj.search([('id', '=', res_id)])
                            if record:
                                record.write(result)
                            else:
                                obj.create(result)
                        else:
                            obj.create(result)
        return True

    @api.model
    def preview_odoo(self, connection, lines):
        if connection:
            odoo_base = connection.connect()
            for line in lines:
                obj = odoo_base.env[line['model']]
                if connection.odoo_company_id:
                    obj = obj.with_context(allowed_company_ids=[connection.odoo_company_id])
                line['result'] = obj.search_read(
                    domain=line.get('domain', []),
                    offset=line.get('offset', 0),
                    limit=line.get('limit', 0),
                    fields=line['fields'],
                )
        return json.dumps(lines, indent=2)
