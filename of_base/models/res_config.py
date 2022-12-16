# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class OFConnectorConfigSettings(models.TransientModel):
    _name = 'of.connector.config.settings'
    _inherit = 'res.config.settings'
    _description = "Configure connectors"

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
