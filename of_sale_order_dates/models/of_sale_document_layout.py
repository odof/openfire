# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleDocumentLayout(models.TransientModel):
    _inherit = "of.sale.document.layout"

    # Invoice settings
    pdf_technical_visit_info_move = fields.Boolean(related="company_id.pdf_technical_visit_info_move", readonly=False)

    # Sale settings
    pdf_technical_visit_info = fields.Boolean(related="company_id.pdf_technical_visit_info", readonly=False)
    pdf_requested_week = fields.Boolean(related="company_id.pdf_requested_week", readonly=False)
