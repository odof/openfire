# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_hide_remaining_balance = fields.Boolean(
        string="(OF) Hide remaining balance",
        help="If you check this box, the remaining balance will be hidden in the interventions.",
    )
    of_company_choice = fields.Selection(
        selection=[
            ('contact', "The contact's company"),
            ('user', "The user's company"),
        ],
        string="(OF) Company choice for interventions",
        default='contact',
        help="Defines the company in which the interventions, requests for interventions, after-sales services and "
        "installed parks will be created.",
    )
    of_automatic_sectors = fields.Boolean(
        string="(OF) Auto. Sectors assignation",
        help="If you check this box, the sectors will be assigned automatically when the contact is created.",
    )
