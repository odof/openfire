# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_sale_product_standard.tests.common import TestOFProductStandardCommon


class TestOFProductStandardSaleLineName(TestOFProductStandardCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_standard_test = cls.create_product(
            {
                'name': 'Product Standard Test',
                'standard_price': 40,
                'list_price': 100,
                'brand_id': cls.product_brand_c.id,  # brand with show_in_sales set to False
                'default_code': f'{cls.product_brand_c.code}_PST_123',
                'of_manufacturer_description': False,
                'of_standard_id': cls.product_standard.id,
            }
        )

    def test_01_sale_order_line_compute_name(self):
        """Test that the name of the sale order line is correctly computed when the product has a standard"""
        order = self.env['sale.order'].create(self._prepare_sale_order_values(dict(product=self.product_standard_test)))
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(
            order.order_line[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )

        # Change the standard of the product before adding a new line
        self.product_standard_test.of_standard_id = self.product_standard2.id
        order.write(
            {
                'order_line': [
                    Command.create(
                        {
                            'product_id': self.product_standard_test.id,
                            'product_uom_qty': 1,
                            'price_unit': 100,
                        }
                    )
                ]
            }
        )

        # Check that the name of the lines is correctly computed
        # The first line should not have changed
        # The second line should have the new standard
        self.assertEqual(len(order.order_line), 2)
        self.assertEqual(
            order.order_line[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )
        self.assertEqual(
            order.order_line[1].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S2 : This is the standard 2",
        )

        # Remove the standard of the product before adding a new line
        self.product_standard_test.of_standard_id = False

        # Add a new line
        order.write(
            {
                'order_line': [
                    Command.create(
                        {
                            'product_id': self.product_standard_test.id,
                            'product_uom_qty': 1,
                            'price_unit': 100,
                        }
                    )
                ]
            }
        )

        # Check that the name of the lines is correctly computed
        # The first two lines should not have changed but the third line should not have the standard
        self.assertEqual(len(order.order_line), 3)
        self.assertEqual(
            order.order_line[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )
        self.assertEqual(
            order.order_line[1].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S2 : This is the standard 2",
        )
        self.assertEqual(
            order.order_line[2].name,
            "[BC_PST_123] Product Standard Test",
        )
