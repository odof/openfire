# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id(self):
        super()._onchange_sale_order_template_id()
        for order in self.filtered('sale_order_template_id'):
            order.fiscal_position_id = order.sale_order_template_id.of_fiscal_position_id
            order.payment_term_id = order.sale_order_template_id.of_payment_term_id
            order.of_custom_document_ids = order.sale_order_template_id.of_custom_document_ids
