# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_customer_state = fields.Selection(related='partner_id.of_customer_state', required=False)
