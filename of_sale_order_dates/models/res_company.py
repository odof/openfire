# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Invoice settings
    pdf_technical_visit_info_move = fields.Boolean(
        string="(OF) Technical visit date",
        help="Displays the technical visit in top information block in Invoice PDF report ?",
        default=False,
    )

    # Sale settings
    pdf_technical_visit_info = fields.Boolean(string="Technical visit date", default=True)
    pdf_requested_week = fields.Boolean(string="Requested week", default=False)
