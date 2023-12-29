# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFOrderMainProduct(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.category_main_product = cls.env['product.category'].create(
            {
                'name': 'Main Product',
                'of_main_product': True,
            }
        )

        cls.product_main_product = cls.create_product(
            {
                'name': 'Product Main Product',
                'categ_id': cls.category_main_product.id,
                'default_code': 'BA_PMP_123',
            }
        )

    def test_01_sale_order_main_product(self):
        """Test that the main product is set when the product is in a main product category."""

        order = self.env['sale.order'].create(self._prepare_sale_order_values(dict(product=self.product_main_product)))

        self.assertEqual(
            order.order_line.filtered(lambda line: line.of_main_product).product_id, self.product_main_product
        )

    def test_02_sale_order_main_product(self):
        """Test that the main product is not set when the product is not in a main product category."""

        order = self.env['sale.order'].create(self._prepare_sale_order_values())

        self.assertEqual(
            order.order_line.filtered(lambda line: line.of_main_product).product_id,
            self.env['product.product'].browse(),
        )
