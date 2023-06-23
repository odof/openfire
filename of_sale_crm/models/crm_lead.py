# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    geo_lat = fields.Float(related='partner_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='partner_id.geo_lng', readonly=True)
    precision = fields.Selection(related='partner_id.precision')
    of_customer_state = fields.Selection(related='partner_id.of_customer_state', required=False)
    of_is_lead_warn = fields.Boolean(string="Leads warning")
