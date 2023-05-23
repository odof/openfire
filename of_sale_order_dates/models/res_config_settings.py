# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pdf_requested_week = fields.Boolean(
        string="Requested week", config_parameter='of.sale.order.dates.pdf_requested_week'
    )
