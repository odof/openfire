# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id(self):
        res = super()._onchange_sale_order_template_id()
        sale_order_template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        if sale_order_template.of_order_type_id:
            self.type_id = sale_order_template.of_order_type_id.id
        return res
