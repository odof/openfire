# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestSaleOrderLineDescription(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_manufacturer_test = cls.create_product(
            {
                'name': 'Product Manufacturer Test',
                'standard_price': 40,
                'list_price': 100,
                'brand_id': cls.product_brand_c.id,  # brand with show_in_sales set to False
                'default_code': f'{cls.product_brand_c.code}_PMT_123',
                'of_manufacturer_description': False,
            }
        )

        cls.order_values = cls._prepare_sale_order_values(cls, dict(product=cls.product_manufacturer_test))

    def test_01_of_sale_order_line_description_both(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'both',
        the name of the sale order line should be the product name + the manufacturer description.
        """
        self.env.user.company_id.show_manufacturer_description = 'both'

        order = self.env['sale.order'].create(self.order_values)
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BC_PMT_123] Product Manufacturer Test")

        self.product_manufacturer_test.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self.order_values)
        order2_line = order2.order_line[0]
        self.assertEqual(
            order2_line.name, "[BC_PMT_123] Product Manufacturer Test\nThis is the manufacturer description"
        )

    def test_02_of_sale_order_line_description_manufacturer_sales(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'sales',
        the name of the sale order line should be the product name + the manufacturer description.
        """
        self.env.user.company_id.show_manufacturer_description = 'sales'

        order = self.env['sale.order'].create(self.order_values)
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BC_PMT_123] Product Manufacturer Test")

        self.product_manufacturer_test.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self.order_values)
        order2_line = order2.order_line[0]
        self.assertEqual(
            order2_line.name, "[BC_PMT_123] Product Manufacturer Test\nThis is the manufacturer description"
        )

    def test_03_of_sale_order_line_description_manufacturer_invoices(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'invoices',
        the manufacturer description should not be added to the name of the sale order line.
        """
        self.env.user.company_id.show_manufacturer_description = 'invoices'

        order = self.env['sale.order'].create(self.order_values)
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BC_PMT_123] Product Manufacturer Test")

        self.product_manufacturer_test.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self.order_values)
        order2_line = order2.order_line[0]
        self.assertEqual(order2_line.name, "[BC_PMT_123] Product Manufacturer Test")

    def test_04_of_sale_order_line_description_manufacturer_no(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'invoices',
        the manufacturer description should not be added to the name of the sale order line.
        """
        self.env.user.company_id.show_manufacturer_description = 'no'

        order = self.env['sale.order'].create(self.order_values)
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BC_PMT_123] Product Manufacturer Test")

        self.product_manufacturer_test.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self.order_values)
        order2_line = order2.order_line[0]
        self.assertEqual(order2_line.name, "[BC_PMT_123] Product Manufacturer Test")
