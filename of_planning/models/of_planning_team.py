# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

import pytz

from odoo import api, fields, models


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class OFPlanningTeam(models.Model):
    _name = 'of.planning.team'
    _description = "Intervention team"
    _order = "sequence, name"

    @api.model
    def _domain_employee_ids(self):
        return ['|', ('of_is_operator', '=', True), ('of_is_salesperson', '=', True)]

    def _default_tz(self):
        return self.env.user.tz or 'Europe/Paris'

    name = fields.Char(string="Team", size=128, required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(help="Display order (smaller displayed first)")
    note = fields.Text(string="Description")
    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        relation='of_team_employee_rel',
        column1='team_id',
        column2='employee_id',
        string="Employees",
        domain=lambda self: self._domain_employee_ids(),
    )
    category_ids = fields.Many2many(
        comodel_name='hr.employee.category',
        relation='of_team_category_rel',
        column1='team_id',
        column2='category_id',
        string="Categories",
    )
    event_ids = fields.One2many(
        comodel_name='calendar.event', inverse_name='of_team_id', string="Linked interventions", copy=False
    )
    task_ids = fields.Many2many(
        comodel_name='of.planning.task',
        relation='of_team_task_rel',
        column1='team_id',
        column2='task_id',
        string="Skills",
    )
    color_ft = fields.Char(string="Font color", help="Choose your color", default="#0D0D0D")
    color_bg = fields.Char(string="Background color", help="Choose your color", default="#F0F0F0")
    tz = fields.Selection(
        selection=_tz_get,
        string="Timezone",
        required=True,
        default=lambda self: self._default_tz(),
        help="Timezone of the intervention team",
    )
    tz_offset = fields.Char(compute='_compute_tz_offset', string="Timezone offset", invisible=True)

    @api.depends('tz')
    def _compute_tz_offset(self):
        for team in self:
            team.tz_offset = datetime.now(pytz.timezone(team.tz or 'GMT')).strftime('%z')
