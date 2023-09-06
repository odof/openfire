# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleOrderLineBrand(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_brand_use_desc = cls.env['of.product.brand'].create(
            {
                'name': "Test Brand Use Description",
                'code': "TBUD",
                'use_brand_description_sale': True,
                'description_sale': "Brand Description\nProduct : {{object.name}}",
                'show_in_sales': True,
                'partner_id': cls.supplier_a.id,
            }
        )
        cls.product_brand_dont_use_desc = cls.env['of.product.brand'].create(
            {
                'name': "Test Brand No Description",
                'code': "TBNUD",
                'use_brand_description_sale': False,
                'description_sale': "Brand Description\nProduct : {{object.name}}",
                'show_in_sales': True,
                'partner_id': cls.supplier_a.id,
            }
        )

    def test_01_of_product_brand_id(self):
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_use_desc.id,
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
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_use_desc.id,
            }
        )

        order = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = product
                self.assertEqual(
                    line_form.name,
                    'Test Brand Use Description - Test Product Use Desc\nBrand Description\n'
                    'Product : Test Product Use Desc',
                )

    def test_03_compute_name_no_use_description(self):
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_dont_use_desc.id,
            }
        )

        order = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = product
                self.assertEqual(line_form.name, 'Test Brand No Description - Test Product Use Desc')
