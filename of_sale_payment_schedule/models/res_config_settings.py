# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pdf_payment_schedule = fields.Boolean(
        string="Payment schedule", config_parameter='of.sale.report.setting.pdf_payment_schedule')
