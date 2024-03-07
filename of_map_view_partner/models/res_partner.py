# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Map view fields
    of_partner_phones = fields.Char(string="Phones", compute='_compute_of_popin_data')

    def _compute_of_popin_data(self):
        for partner in self:
            phones = partner.mapped('of_phone_number_ids.number_display')
            phones = [phone for phone in phones if phone]  # Remove empty phone numbers (e.g. [None, False])
            partner.of_partner_phones = ', '.join(phones) if phones else ''
