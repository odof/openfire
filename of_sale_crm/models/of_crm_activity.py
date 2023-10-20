# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMActivity(models.Model):
    _inherit = 'of.crm.activity'

    order_id = fields.Many2one(comodel_name='sale.order', string="Sale Order", ondelete='cascade')
    trigger_type = fields.Selection(
        selection=[('at_creation', "At creation"), ('at_validation', "At validation")], string="Trigger"
    )
