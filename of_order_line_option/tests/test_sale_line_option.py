# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestSaleLineOption(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.order_option_sale_price = cls.env['of.order.line.option'].create(
            {
                'name': "Option 1",
                'description_update': "Option 1 description",
                'sale_price_update': True,
                'sale_price_update_type': 'fixed',
                'sale_price_update_value': 10,
            }
        )
        cls.order_option_purchase_price = cls.env['of.order.line.option'].create(
            {
                'name': "Option 2",
                'description_update': "Option 2 description",
                'purchase_price_update': True,
                'purchase_price_update_type': 'fixed',
                'purchase_price_update_value': 10,
            }
        )

        cls.purchase_order = cls.env['purchase.order'].create(
            {
                'partner_id': cls.supplier_a.id,
                'partner_ref': 'PO-001',
            }
        )

        cls.product_option = cls.create_product(
            {
                'name': 'Test Product Option',
                'brand_id': cls.product_brand_b.id,  # Brand with 'use_brand_description_sale' = False
                'default_code': f'{cls.product_brand_b.code}_TPO_123',
                # list_price = 100
                # standard_price = 40
            }
        )

    def test_01_sale_line_option_selection(self):
        """Test sale line option selection"""

        with Form(self.env['sale.order'].create(self._prepare_empty_sale_order_values())) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.product_option
                line_form.of_order_line_option_id = self.order_option_sale_price
            order = order_form.save()
        self.assertEqual(order.order_line[0].name, "[BB_TPO_123] Brand B - Test Product Option\nOption 1 description")

    def test_02_sale_line_option_modification(self):
        """Test sale line option modification. Description should be updated when option is selected"""
        with Form(self.env['sale.order'].create(self._prepare_empty_sale_order_values())) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.product_option
                line_form.of_order_line_option_id = self.order_option_sale_price
                self.assertEqual(line_form.name, "[BB_TPO_123] Brand B - Test Product Option\nOption 1 description")
                line_form.of_order_line_option_id = self.order_option_purchase_price
                self.assertEqual(line_form.name, "[BB_TPO_123] Brand B - Test Product Option\nOption 2 description")

    def test_03_sale_line_option_sale_price_update_fixed(self):
        """Test sale line option sale price update fixed. Price should be updated when option is selected and
        price should be reset when option is deselected when clicking on reset button."""
        with Form(self.env['sale.order'].create(self._prepare_empty_sale_order_values())) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.product_option
                line_form.of_order_line_option_id = self.order_option_sale_price
                self.assertEqual(line_form.price_unit, 110)
                line_form.of_order_line_option_id = self.env['of.order.line.option']
                self.assertEqual(line_form.price_unit, 110)
                line_form.of_order_line_option_id = self.order_option_sale_price
                self.assertEqual(line_form.price_unit, 120)

            order = order_form.save()
        order.order_line.action_button_reset_option()
        self.assertEqual(order.order_line[0].price_unit, 100)

    def test_04_sale_line_option_purchase_price_update_fixed(self):
        """Test purchase line option purchase price update fixed. Price should be updated when option is selected.
        There is no reset button for purchase order lines."""
        with Form(self.purchase_order) as purchase_form:
            with purchase_form.order_line.new() as line_form:
                line_form.product_id = self.product_option
                line_form.of_order_line_option_id = self.order_option_purchase_price
                self.assertEqual(line_form.price_unit, 50)
                line_form.of_order_line_option_id = self.env['of.order.line.option']
                self.assertEqual(line_form.price_unit, 50)
                line_form.of_order_line_option_id = self.order_option_purchase_price
                self.assertEqual(line_form.price_unit, 60)

    def test_05_sale_line_option_sale_price_update_percentage(self):
        """Test sale line option sale price update percentage. Price should be updated when option is selected and
        price should be reset when option is deselected when clicking on reset button."""
        self.order_option_sale_price.sale_price_update_type = 'percent'
        self.order_option_sale_price.sale_price_update_value = 20

        with Form(self.env['sale.order'].create(self._prepare_empty_sale_order_values())) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.product_option
                line_form.of_order_line_option_id = self.order_option_sale_price
                self.assertEqual(line_form.price_unit, 120)
                line_form.of_order_line_option_id = self.env['of.order.line.option']
                self.assertEqual(line_form.price_unit, 120)
                line_form.of_order_line_option_id = self.order_option_sale_price
                self.assertEqual(line_form.price_unit, 144)

            order = order_form.save()
        order.order_line.action_button_reset_option()
        self.assertEqual(order.order_line[0].price_unit, 100)

    def test_06_sale_line_option_purchase_price_update_percentage(self):
        """Test purchase line option purchase price update percentage. Price should be updated when option is selected
        and there is no reset button for purchase order lines."""
        self.order_option_sale_price.purchase_price_update_type = 'percent'
        self.order_option_sale_price.purchase_price_update_value = 20
        with Form(self.purchase_order) as purchase_form:
            with purchase_form.order_line.new() as line_form:
                line_form.product_id = self.product_option
                line_form.of_order_line_option_id = self.order_option_purchase_price
                self.assertEqual(line_form.price_unit, 50)
                line_form.of_order_line_option_id = self.env['of.order.line.option']
                self.assertEqual(line_form.price_unit, 50)
                line_form.of_order_line_option_id = self.order_option_purchase_price
                self.assertEqual(line_form.price_unit, 60)
