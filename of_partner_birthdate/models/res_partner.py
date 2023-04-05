# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_birthdate_short = fields.Char(
        string="Birthdate (MM-DD)",
        compute='_compute_of_birthdate_short',
        search='_search_of_birthdate_short',
        help="Birthdate in format MM-DD (for search purpose only)",
    )

    def _compute_of_birthdate_short(self):
        for partner in self:
            partner.of_birthdate_short = partner.birthdate_date.strftime('%m-%d') if partner.birthdate_date else False

    @api.model
    def _search_of_birthdate_short(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        return [('birthdate_date', operator, value)]
