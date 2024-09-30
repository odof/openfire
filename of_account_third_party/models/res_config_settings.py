# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_customer_code = fields.Char(
        related="company_id.of_customer_code", string="Customer code", readonly=False, required=True
    )
    of_supplier_code = fields.Char(
        related="company_id.of_supplier_code", string="Supplier code", readonly=False, required=True
    )
