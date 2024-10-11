# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale_product_standard.tests.common import TestOFProductStandardCommon


class TestProductStandard(TestOFProductStandardCommon):
    def setUp(self):
        super().setUp()
        self.product = self.env["product.template"].create(
            {
                "name": "Test Product",
                "of_standard_id": self.product_standard.id,
                "categ_id": self.env.ref("product.product_category_all").id,
            }
        )
        self.product2 = self.env["product.template"].create(
            {
                "name": "Test Product 2",
                "of_standard_id": self.product_standard.id,
                "categ_id": self.env.ref("product.product_category_all").id,
            }
        )

    def test_01_write_standard_description(self):
        """Test that the standard description is updated on the products when the standard is updated"""
        self.assertEqual(self.product.of_standard_description, self.product_standard.description)
        self.assertEqual(self.product2.of_standard_description, self.product_standard.description)
        self.product_standard.write({"description": "New description"})
        self.assertEqual(self.product.of_standard_description, "New description")
        self.assertEqual(self.product2.of_standard_description, "New description")

    def test_02_write_standard_description(self):
        """Test that the standard description is not updated on the products when the standard is updated if the
        product has a custom description"""
        self.assertEqual(self.product.of_standard_description, self.product_standard.description)
        self.assertEqual(self.product2.of_standard_description, self.product_standard.description)
        self.product.write({"of_standard_description": "This is a test standard updated by user"})
        self.product_standard.write({"description": "New description - modified"})
        self.assertEqual(self.product.of_standard_description, "This is a test standard updated by user")
        self.assertEqual(self.product2.of_standard_description, "New description - modified")
