# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'of.sale.document.layout'

    pdf_payment_schedule = fields.Boolean(
        related='company_id.pdf_payment_schedule',
        readonly=False,
    )
