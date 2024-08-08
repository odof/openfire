# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class ESBHistory(models.Model):
    _name = 'esb.history'
    _rec_name = 'ttype'

    ttype = fields.Char()
    uuid = fields.Char()
    date = fields.Datetime()
    history = fields.Text()
    user = fields.Many2one(comodel_name='res.users')

    @api.model
    def cron_history_build(self):
        self.build_history()

    @api.model
    def build_history(self):
        # on va chercher dans le bus les logs sur le channel history, regroupé par uuid
        lines = self.env['esb.bus'].read_group(
            domain=[('ttype', '=', self.env.ref('of_esb.type_logs').id), ('channel', '=', 'history')],
            fields=['date', 'data', 'uuid'],
            groupby=['uuid'],
        )
        for line in lines:
            res = []
            user_id = False
            uuid = line['uuid']
            lines_data = self.env['esb.data'].search([('properties', 'like', uuid)])

            for line_data in lines_data:
                in_data = json.loads(line_data.in_data)
                if in_data.get('trigger', False):
                    user_id = in_data.get('user_id', False)
                if ttype := in_data.get('type', False):
                    if ttype == 'trigger':
                        history_value = {
                            'date': str(line_data.create_date),
                            'type': 'trigger',
                            'name': in_data.get('name', ''),
                            'state': '',
                        }
                        res.append(history_value)
                    if ttype == 'service':
                        history_value = {
                            'date': str(line_data.create_date),
                            'type': 'service',
                            'name': in_data.get('name', ''),
                            'state': '',
                        }
                        res.append(history_value)
                        job = self.env['queue.job'].search([('uuid', '=', in_data.get('job'))])
                        history_value = {
                            'date': str(job.date_started),
                            'type': 'job',
                            'name': in_data.get('job'),
                            'state': job.state,
                        }
                        res.append(history_value)
            logger.info(res)
            if len(lines_data) > 0:
                value = {
                    'ttype': 'trigger',
                    'uuid': uuid,
                    'date': lines_data[0].create_date,
                    'user': user_id,
                    'history': json.dumps(res),
                }
                self.create(value)

        # on supprime les logs une fois dans l'history
