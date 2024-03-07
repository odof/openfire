# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFEquipment(models.Model):
    _inherit = 'of.equipment'

    # Map view fields
    site_phones = fields.Char(string="Phones", compute='_compute_of_popin_data')

    def _compute_of_popin_data(self):
        for equipment in self:
            site_phones = equipment.site_address_id.mapped('of_phone_number_ids.number_display')
            equipment.site_phones = ', '.join(site_phones) if site_phones else ''
