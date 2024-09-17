# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_team_alert_intervention_sms = fields.Boolean(
        string="Teams alert",
        help="Send SMS alert to the teams with summary of the intervention for the next day",
    )

    of_customer_alert_intervention_sms = fields.Boolean(
        string="Customers alert",
        help="Send SMS alert to the customers with summary of the intervention for the next day",
    )
