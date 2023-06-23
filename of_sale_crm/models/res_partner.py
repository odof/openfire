# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_customer_state = fields.Selection(
        selection=[('lead', "Prospect"), ('customer', "Signed customer"), ('other', "Other")],
        string="State",
        default='lead',
        help="This field is only useful for customer partners."
        "A customer is considered a prospect as long as he/she has neither confirmed an order nor validated "
        "an invoice. This field is updated automatically on order confirmation and invoice validation.",
    )
    of_is_lead_warn = fields.Boolean(string="Leads warning")

    def _add_missing_default_values(self, values):
        if not values.get('of_customer_state', False):
            values['of_customer_state'] = 'lead'
        return super()._add_missing_default_values(values)
