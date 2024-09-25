# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'of.invoice.document.layout'

    pdf_invoice_payment_schedule = fields.Boolean(
        related='company_id.pdf_invoice_payment_schedule',
        readonly=False,
    )
