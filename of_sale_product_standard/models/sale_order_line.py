# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id')
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if not (line.product_id.of_standard_id.active and line.product_id.of_standard_id.display_docs):
                continue
            if not line.order_partner_id.is_public:
                line = line.with_context(lang=line.order_partner_id.lang)
            if not line.product_id.of_description_standard:
                continue
            line.name = (
                line.name
                + "\n"
                + _("%s compliant: %s") % (line.product_id.of_standard_id.code, line.product_id.of_description_standard)
            )
