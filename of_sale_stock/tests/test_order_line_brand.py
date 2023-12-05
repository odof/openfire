# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFSaleOrderLineBrand(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def _prepare_empty_sale_order_values(self):
        return {
            'partner_id': self.customer_a.id,
            'partner_invoice_id': self.customer_a.id,
            'partner_shipping_id': self.customer_a.id,
            'pricelist_id': self.default_pricelist.id,
            'fiscal_position_id': self.fiscal_pos_5_5.id,
        }

    def test_01_of_product_brand_id(self):
        """Test if the brand is correctly set on the sale order line depending on product set on the line."""
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_a.id,
            }
        )

        order = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = product

        order = order_form.save()
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line[0].of_product_brand_id, product.brand_id)

    def test_02_compute_name_use_description(self):
        """Test the compute name of the sale order line when the brand has use_brand_description_sale set to True."""
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_a.id,
            }
        )

        order = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = product
                self.assertEqual(
                    line_form.name,
                    'Brand A - Test Product Use Desc\nBrand A Description\nProduct : Test Product Use Desc',
                )

    def test_03_compute_name_no_use_description(self):
        """Test the compute name of the sale order line when the brand has use_brand_description_sale set to False."""
        product = self.create_product(
            {
                'name': 'Test Product No Use Desc',
                'brand_id': self.product_brand_b.id,
            }
        )

        order = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = product
                self.assertEqual(line_form.name, 'Brand B - Test Product No Use Desc')

    def test_04_compute_name_no_use_description_with_manufacturer_desc(self):
        """Test the compute name of the sale order line when the brand has use_brand_description_sale set to False
        and the product has a manufacturer description.
        """

        product = self.create_product(
            {
                'name': 'Test Product No Use Desc',
                'brand_id': self.product_brand_b.id,
                'of_manufacturer_description': False,
            }
        )

        self.env.user.company_id.show_manufacturer_description = 'sales'

        order = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = product
        order = order_form.save()

        order_line = order.order_line[0]
        self.assertEqual(order_line.name, "Brand B - Test Product No Use Desc")

        product.of_manufacturer_description = "This is the manufacturer description"

        order = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = product
        order2 = order_form.save()

        order2_line = order2.order_line[0]
        self.assertEqual(order2_line.name, "Brand B - Test Product No Use Desc\nThis is the manufacturer description")
