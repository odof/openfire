# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    @api.depends('product_id')
    def _compute_name(self):
        super()._compute_name()
        for option in self:
            if not option.product_id:
                continue
            option.name = option.product_id._recompute_product_name()
