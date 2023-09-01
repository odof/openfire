# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestSaleOrderLine(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_of_sale_order_line_description_both(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'both',
        the name of the sale order line should be the product name + the manufacturer description.
        """
        self.env.user.company_id.show_manufacturer_description = 'both'

        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BA_PCA_123] Product Consu A")

        self.product_consu_a.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self._prepare_sale_order_values())
        order2_line = order2.order_line[0]
        self.assertEqual(order2_line.name, "[BA_PCA_123] Product Consu A\nThis is the manufacturer description")

    def test_02_of_sale_order_line_description_manufacturer_sales(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'sales',
        the name of the sale order line should be the product name + the manufacturer description.
        """
        self.env.user.company_id.show_manufacturer_description = 'sales'

        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BA_PCA_123] Product Consu A")

        self.product_consu_a.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self._prepare_sale_order_values())
        order2_line = order2.order_line[0]
        self.assertEqual(order2_line.name, "[BA_PCA_123] Product Consu A\nThis is the manufacturer description")

    def test_03_of_sale_order_line_description_manufacturer_invoices(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'invoices',
        the manufacturer description should not be added to the name of the sale order line.
        """
        self.env.user.company_id.show_manufacturer_description = 'invoices'

        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BA_PCA_123] Product Consu A")

        self.product_consu_a.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self._prepare_sale_order_values())
        order2_line = order2.order_line[0]
        self.assertEqual(order2_line.name, "[BA_PCA_123] Product Consu A")

    def test_04_of_sale_order_line_description_manufacturer_no(self):
        """Test the name of the sale order line.
        If the manufacturer description is set and the company parameter is set to 'invoices',
        the manufacturer description should not be added to the name of the sale order line.
        """
        self.env.user.company_id.show_manufacturer_description = 'no'

        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "[BA_PCA_123] Product Consu A")

        self.product_consu_a.of_manufacturer_description = "This is the manufacturer description"

        order2 = self.env['sale.order'].create(self._prepare_sale_order_values())
        order2_line = order2.order_line[0]
        self.assertEqual(order2_line.name, "[BA_PCA_123] Product Consu A")
