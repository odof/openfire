# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.models import expression


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    of_update_date = fields.Datetime(
        string='Update date',
        help="Most recent update date of every elements in the intervention",
        default=fields.Datetime.now(),
    )

    def write(self, vals):
        vals['of_update_date'] = fields.Datetime.now()
        return super().write(vals)

    @api.model
    def action_update_date(self, domain_obj):
        of_mobile_days_before = (
            self.env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_before', 0)
        )
        of_mobile_days_after = (
            self.env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_after', 0)
        )

        now = fields.Datetime.now()
        today = fields.Date.today()
        before = today + relativedelta(days=-int(of_mobile_days_before))
        after = today + relativedelta(days=int(of_mobile_days_after))

        domain = [
            ('start', '>=', fields.Date.to_string(before)),
            ('start', '<=', fields.Date.to_string(after)),
            ('of_state', 'not in', ['cancel', 'postponed']),
        ]

        domain = expression.AND([domain, domain_obj])

        if interventions := self.env['calendar.event'].sudo().search(domain):
            interventions.write({'of_update_date': now})
