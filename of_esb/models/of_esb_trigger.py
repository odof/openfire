# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import uuid

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from odoo.addons.http_routing.models.ir_http import slugify_one

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


logger = logging.getLogger(__name__)


class ESBTrigger(models.Model):
    _name = 'of.esb.trigger'

    name = fields.Char()
    ttype = fields.Selection(
        [('scheduler', 'Scheduler'), ('webhook', 'Webhook')], default='scheduler', required=True, string='Type'
    )
    date_exec = fields.Datetime(string="Date of execution")
    interval_number = fields.Integer(default=1)
    interval_type = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Interval Unit',
        default='months',
    )
    exec_active = fields.Boolean(default=True)
    data = fields.Many2one(comodel_name='of.esb.data')
    data_channel = fields.Char()
    data_type = fields.Many2one(
        comodel_name='of.esb.type.bus',
        string='Type of bus',
        default=lambda self: self.env.ref('of_esb.type_scheduler').id,
    )
    # Type webhook
    slug_name = fields.Char(compute='_compute_slug_name', store=True)
    public = fields.Boolean(help="Check this to make this trigger accessible with the url /webhook/")
    security = fields.Many2one(comodel_name='of.esb.security')
    uuid = fields.Char(default=lambda r: uuid.uuid4())

    @api.depends('name')
    def _compute_slug_name(self):
        for record in self:
            if record.public:
                record.slug_name = f"/webhook/{slugify_one(record.name)}"
            else:
                record.slug_name = ""

    @api.model
    def cron_execute(self):
        now = fields.Datetime.now()
        triggers = self.search([('exec_active', '=', True), ('ttype', '=', 'scheduler'), ('date_exec', '<=', now)])
        for trigger in triggers:
            bus = self.env['of.esb.bus'].send_bus(
                ttype=trigger.data_type, channel=trigger.data_channel, data=trigger.data.in_data
            )

            if trigger.interval_number > 0:
                interval = _intervalTypes[trigger.interval_type](trigger.interval_number)
                trigger.date_exec += interval
            else:
                trigger.date_exec = False

            data = {
                'type': 'trigger',
                'id': trigger.id,
                'name': trigger.name,
                'user_id': self.env.user.id,
                'uuid': bus.uuid,
            }
            properties = {'uuid': bus.uuid}
            self.env['of.esb.bus'].send_bus(
                ttype=self.env.ref('of_esb.type_logs'), channel='history', data=data, properties=properties
            )
