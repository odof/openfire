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

    of_historical_ids = fields.One2many(
        comodel_name='calendar.event',
        compute="_compute_historical_ids",
    )

    of_coming_ids = fields.One2many(
        comodel_name='calendar.event',
        compute="_compute_coming_ids",
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

    @api.depends('of_partner_id', 'of_address_id')
    def _compute_historical_ids(self):
        limit = self.env['ir.config_parameter'].sudo().get_param('of_mobile.history_limit')
        today = fields.Datetime.from_string(fields.Date.today())
        limit_date = today - relativedelta(months=int(limit))
        for interv in self:
            if interv.of_address_id:
                interventions = interv.of_address_id.of_intervention_address_ids
            elif interv.of_partner_id:
                interventions = interv.of_partner_id.of_intervention_partner_ids
            else:
                continue

            interv.of_historical_ids = interventions.filtered(
                lambda i: self._filterHistoricalIntervention(i, interv.start, limit_date)
            )

    def _filterHistoricalIntervention(self, historical_intervention, intervention_date, limit_date):
        return intervention_date > historical_intervention.start > limit_date

    @api.depends('of_partner_id', 'of_address_id')
    def _compute_coming_ids(self):
        for interv in self:
            if interv.of_address_id:
                interventions = interv.of_address_id.of_intervention_address_ids
            elif interv.of_partner_id:
                interventions = interv.of_partner_id.of_intervention_partner_ids
            else:
                continue

            interv.of_coming_ids = interventions.filtered(
                lambda i: self._filterComingIntervention(i, interv.start)
            ).sorted(key=lambda x: x.start)

    def _filterComingIntervention(self, coming_intervention, intervention_date):
        return intervention_date < coming_intervention.start
