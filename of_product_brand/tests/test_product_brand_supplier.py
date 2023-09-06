# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_product_brand.tests.common import TestOFProductCommon


class TestProductBrandSupplier(TestOFProductCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_product_creation_is_supplier_ok(self):
        """Test that supplier data is correctly set on product creation"""
        with Form(self.env['product.template']) as product_form:
            product_form.name = "Test Product Supplier"
            product_form.categ_id = self.env.ref('product.product_category_all')
            product_form.brand_id = self.test_brand
            product = product_form.save()
        self.assertEqual(len(product.seller_ids), 1)
        self.assertEqual(product.seller_ids.partner_id, self.test_supplier)

    def test_02_product_brand_update_is_supplier_ok(self):
        """Test that supplier data is correctly set on product brand update"""
        with Form(self.env['product.template']) as product_form:
            product_form.name = "Test Product Supplier"
            product_form.categ_id = self.env.ref('product.product_category_all')
            product_form.brand_id = self.test_brand
            product = product_form.save()

        with Form(product) as product_form:
            product_form.brand_id = self.another_brand
            product = product_form.save()

        self.assertEqual(len(product.seller_ids), 1)
        self.assertEqual(product.seller_ids.partner_id, self.another_supplier)
