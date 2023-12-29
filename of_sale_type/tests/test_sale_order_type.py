# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale_type.tests.common import TestOFSaleOrderTypeCommon


class TestSaleOrderType(TestOFSaleOrderTypeCommon):
    def setUp(self):
        super().setUp()
        self.sale_order_type_1 = self.env['sale.order.type'].create(
            {
                'name': "Type 1",
            }
        )
        self.sale_order_template_1.of_order_type_id = self.sale_order_type_1.id

    def test_01_onchange_sale_order_template_id(self):
        """Test onchange sale_order_template_id. The sale_order_template has an order type.
        Sale Order should have the same order type."""

        order_values = self._prepare_sale_order_values()
        order_values['sale_order_template_id'] = self.sale_order_template_1.id
        sale_order = self.env['sale.order'].create(order_values)
        sale_order._onchange_sale_order_template_id()

        self.assertEqual(sale_order.type_id, self.sale_order_type_1)
