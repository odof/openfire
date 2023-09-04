# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPriceManagementWizardLine(models.TransientModel):
    _inherit = 'of.sale.price.management.wizard.line'

    product_forbidden_discount = fields.Boolean(
        related='order_line_id.of_product_forbidden_discount',
        string="Discount not allowed for this product",
        readonly=True,
    )
