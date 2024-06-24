# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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


class ESBTrigger(models.Model):
    _name = 'esb.trigger'

    name = fields.Char()
    ttype = fields.Selection([('scheduler', 'Scheduler'), ('webhook', 'Webhook')], default='scheduler', required=True)
    date_exec = fields.Datetime(string="Date of execution")
    interval_number = fields.Integer(default=1)
    interval_type = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Interval Unit',
        default='months',
    )
    exec_active = fields.Boolean(default=True)
    data = fields.Many2one(comodel_name='esb.data', required=True)
    data_channel = fields.Char()
    data_type = fields.Char()
    # Type webhook
    slug_name = fields.Char(compute='_compute_slug_name')
    public = fields.Boolean(help="Check this to make this trigger accessible with the url /service/execute/")
    security = fields.Many2one(comodel_name='esb.security', required=True)

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
            value = {'data': trigger.data, 'channel': trigger.data_channel, 'ttype': trigger.data_type}
            self.env['esb.bus'].create(value)
            if trigger.interval_number > 0:
                interval = _intervalTypes[trigger.interval_type](trigger.interval_number)
                trigger.date_exec += interval
            else:
                trigger.date_exec = False
