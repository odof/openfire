# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pdf_payment_schedule = fields.Boolean(
        string="Payment schedule",
        default=True,
    )
