# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

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

        order_values = self._prepare_empty_sale_order_values()
        order_values['order_line'] = [
            Command.create(
                {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                }
            )
        ]
        order = self.env['sale.order'].create(order_values)

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

        order_values = self._prepare_empty_sale_order_values()
        order_values['order_line'] = [
            Command.create(
                {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                }
            )
        ]
        order = self.env['sale.order'].create(order_values)

        self.assertEqual(
            order.order_line[0].name,
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

        order_values = self._prepare_empty_sale_order_values()
        order_values['order_line'] = [
            Command.create(
                {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                }
            )
        ]
        order = self.env['sale.order'].create(order_values)

        self.assertEqual(order.order_line[0].name, 'Brand B - Test Product No Use Desc')

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

        # Set the company to show the manufacturer description on the sale order line
        self.env.user.company_id.show_manufacturer_description = 'sales'

        order_values = self._prepare_empty_sale_order_values()
        order_values['order_line'] = [
            Command.create(
                {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                }
            )
        ]
        order = self.env['sale.order'].create(order_values)

        self.assertEqual(order.order_line[0].name, "Brand B - Test Product No Use Desc")

        # Set a manufacturer description
        product.of_manufacturer_description = "This is the manufacturer description"

        order_values = self._prepare_empty_sale_order_values()
        order_values['order_line'] = [
            Command.create(
                {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                }
            )
        ]
        order2 = self.env['sale.order'].create(order_values)

        # Check that the manufacturer description is added to the name
        self.assertEqual(
            order2.order_line[0].name, "Brand B - Test Product No Use Desc\nThis is the manufacturer description"
        )
