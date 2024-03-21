# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Map view fields
    of_partner_phones = fields.Char(string="Phones", compute='_compute_of_popin_data')
    of_lead_tags = fields.Char(string="Tags", compute='_compute_of_popin_data')

    def _compute_of_popin_data(self):
        for lead in self:
            phones = lead.partner_id.mapped('of_phone_number_ids.number_display')
            lead.of_partner_phones = ', '.join(phones) if phones else ''
            lead.of_lead_tags = ', '.join(lead.tag_ids.mapped('name')) if lead.tag_ids else ''
