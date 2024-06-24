# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one

logger = logging.getLogger(__name__)


class ESBHistory(models.Model):
    _name = 'of.esb.history'
    _rec_name = 'ttype'

    ttype = fields.Char(string="Type")
    uuid = fields.Char()
    date = fields.Datetime()
    history = fields.Text()
    user = fields.Many2one(comodel_name='res.users')
    mermaid = fields.Text(compute='_compute_mermaid')

    @api.model
    def cron_history_build(self):
        self.build_history()

    @api.model
    def build_history(self):
        # on va chercher dans le bus les logs sur le channel history, regroupé par uuid des datas
        lines = self.env['of.esb.bus'].search(
            [('channel', '=', 'history'), ('ttype', '=', self.env.ref('of_esb.type_logs').id)]
        )
        history_lines = {}
        for line in lines:
            properties = json.loads(line.data.properties)
            if data_uuid := properties.get('uuid'):
                if data_uuid in history_lines:
                    history_lines[data_uuid]['history'] += line
                else:
                    history_lines[data_uuid] = {'history': line}

        for uuid in history_lines:
            res = []
            user_id = False
            lines_data = history_lines[uuid]['history'].mapped('data')
            for line_data in lines_data:
                in_data = json.loads(line_data.in_data)
                if ttype := in_data.get('type', False):
                    if ttype == 'trigger':
                        user_id = in_data.get('user_id')
                        history_value = {
                            'date': str(line_data.create_date),
                            'type': 'trigger',
                            'name': in_data.get('name', ''),
                            'state': '',
                            'slug': slugify_one(in_data.get('name', '')),
                        }
                        res.append(history_value)
                    if ttype == 'service':
                        history_value = {
                            'date': str(line_data.create_date),
                            'type': 'service',
                            'name': in_data.get('name', ''),
                            'state': '',
                            'job_id': in_data.get('job'),
                            'slug': slugify_one(in_data.get('name', '')),
                        }
                        res.append(history_value)
                        job = self.env['queue.job'].search([('uuid', '=', in_data.get('job'))])
                        history_value = {
                            'date': str(job.date_started),
                            'type': 'job',
                            'name': in_data.get('job'),
                            'state': job.state,
                            'exec_time': job.exec_time,
                        }
                        res.append(history_value)
            if len(lines_data) > 0:
                value = {
                    'ttype': 'trigger',
                    'uuid': uuid,
                    'date': lines_data[0].create_date,
                    'user': user_id,
                    'history': json.dumps(res),
                }
                history = self.search([('uuid', '=', uuid)])
                if len(history):
                    history.write(value)
                else:
                    self.create(value)

    def _compute_mermaid(self):
        def get_trigger(user, lines):
            trigger = False
            for line in lines:
                if line['type'] == 'trigger':
                    trigger = line
                    break
            if trigger:
                mermaid = f"""{trigger['slug']}-- {user} -->"""
            else:
                mermaid = ""
            return mermaid

        def get_services(trigger, lines):
            mermaid = ""
            services = {}
            jobs = {}

            for line in lines:
                if line['type'] == 'service':
                    services[line['job_id']] = line
                if line['type'] == 'job':
                    jobs[line['name']] = line

            for service in services:
                mermaid_service = f"""{trigger}{services[service]['slug']}
                subgraph "Service: {services[service]['name']} (durée : {jobs[services[service]['job_id']]['exec_time']} secondes)"
                {services[service]['slug']} --> {jobs[services[service]['job_id']]['name']}
                end
                {jobs[services[service]['job_id']]['name']} -.-> {jobs[services[service]['job_id']]['state']}
                """
                mermaid += mermaid_service
            return mermaid

        for record in self:
            if len(record.history) == 0:
                record.mermaid = "graph LR;"
            else:
                mermaid = "graph LR; Trigger --> "
                lines = json.loads(record.history)
                trigger = get_trigger(record.user.display_name, lines)
                services = get_services(trigger, lines)
                mermaid = f"""{mermaid}
                {services}
                """
                record.mermaid = mermaid
