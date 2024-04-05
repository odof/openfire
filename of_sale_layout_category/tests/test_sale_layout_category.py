# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_sale_layout_category.tests.common import TestOFSaleLayoutCategoryCommon


class TestOFSaleOrderLayoutCategory(TestOFSaleLayoutCategoryCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_sale_order_show_product(self):
        """Test that the product line are not displayed when show product toggle is disabled."""

        order = self.env['sale.order'].create(self._prepare_sale_order_values({}))

        with Form(order) as order_form:
            order_form.of_show_products = False

        product_lines = order.order_line.filtered(lambda li: li.display_type is False)

        self.assertEqual(all([line.of_show is False for line in product_lines]), True)

    def test_02_sale_order_show_product(self):
        """
        Test that the product line are displayed when show product toggle is disabled
        and then layout category toggle is disabled too.
        """
        order = self.env['sale.order'].create(self._prepare_sale_order_values({}))

        with Form(order) as order_form:
            order_form.of_show_products = False
            order_form.of_layout_category_active = False

        product_lines = order.order_line.filtered(lambda li: li.display_type is False)

        self.assertEqual(all([line.of_show is True for line in product_lines]), True)

    def test_03_create_sale_order(self):
        """Test that the values of the sale order line is correctly copied to the invoice line values"""
        values = self._prepare_sale_order_values({})
        order = self.env['sale.order'].create(values)
        self.assertEqual(len(order.order_line), 3)

    def test_04_prepare_invoice_line(self):
        """Test that the values of the sale order line is correctly copied to the invoice line values"""
        order = self.env['sale.order'].create(self._prepare_sale_order_values({}))

        # On teste pour une ligne de section
        first_section_line = order.order_line.filtered(lambda li: li.display_type == 'line_section')[0]
        invoice_line = first_section_line._prepare_invoice_line()
        self.assertEqual(invoice_line['of_section_name'], "1")
        self.assertEqual(invoice_line['name'], "Section 1")
        self.assertEqual(invoice_line['of_node_id'], 1)
        self.assertEqual(invoice_line['of_parent_node_id'], 0)
        self.assertEqual(invoice_line['of_level'], 1)
        self.assertEqual(invoice_line['of_position_node'], 0)

        # On teste pour une ligne de produit
        first_order_line = order.order_line.filtered(lambda li: li.display_type is False)[0]
        invoice_line_2 = first_order_line._prepare_invoice_line()
        self.assertEqual(invoice_line_2['of_section_name'], False)
        self.assertEqual(invoice_line_2['of_node_id'], 2)
        self.assertEqual(invoice_line_2['of_parent_node_id'], 1)
        self.assertEqual(invoice_line_2['of_level'], 2)
        self.assertEqual(invoice_line_2['of_position_node'], 1)

    def test_05_prepare_procurement_values(self):
        """Test that the values of the sale order line is correctly prepared for the procurement values"""
        order = self.env['sale.order'].create(self._prepare_sale_order_values({}))

        # On teste pour une ligne de section
        first_section_line = order.order_line.filtered(lambda li: li.display_type == 'line_section')[0]
        procurement_values = first_section_line._prepare_procurement_values()
        self.assertEqual(procurement_values['of_section'], "1 - Section 1")

        # On teste pour une ligne de produit
        first_order_line = order.order_line.filtered(lambda li: li.display_type is False)[0]
        procurement_values = first_order_line._prepare_procurement_values()
        self.assertEqual(procurement_values['of_section'], "1 - Section 1")
