# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_product_brand.tests.common import TestOFProductCommon


class TestOfProductBrand(TestOFProductCommon):
    def setUp(self):
        super().setUp()

        self.product1 = self.env['product.product'].create(
            {
                'name': "Test Product 1",
                'default_code': "BA_001",
                'brand_id': self.product_brand_a.id,
                'categ_id': self.env.ref('product.product_category_all').id,
            }
        )
        self.product2 = self.env['product.product'].create(
            {
                'name': "Test Product 2",
                'default_code': "BA_002",
                'brand_id': self.product_brand_a.id,
                'categ_id': self.env.ref('product.product_category_all').id,
            }
        )

    def test_01_update_products_default_code(self):
        """Test that the default code is updated when the brand is updated"""
        self.assertEqual(self.product1.default_code, 'BA_001')
        self.assertEqual(self.product2.default_code, 'BA_002')
        self.product_brand_a.write({'use_prefix': False})
        self.assertEqual(self.product1.default_code, '001')
        self.assertEqual(self.product2.default_code, '002')
        self.product_brand_a.write({'use_prefix': True})
        self.assertEqual(self.product1.default_code, 'BA_001')
        self.assertEqual(self.product2.default_code, 'BA_002')

    def test_02_update_products_default_code(self):
        """Test that thr brand is emptied when the default code is updated"""
        with self.assertRaises(AssertionError):
            with Form(self.product1) as product_form:
                product_form.default_code = '001'

    def test_03_update_products_default_code(self):
        """Test that the brand is updated when the default code is updated"""
        with Form(self.product1) as product_form:
            product_form.default_code = 'BB_001'

        self.assertEqual(self.product1.default_code, 'BB_001')
        self.assertEqual(self.product1.brand_id, self.product_brand_b)
