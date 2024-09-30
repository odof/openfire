# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_sale_management_template.tests.common import TestOFSaleManagementCommon


class TestOFUpdateTemplateLineDescription(TestOFSaleManagementCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order_template_1.write(
            {
                "sale_order_template_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_consu_a.id,
                            "product_uom_qty": 1,
                        }
                    )
                ]
            }
        )

    def test_01_update_product_brand_ok(self):
        """Test update of product brand"""
        self.product_consu_a.brand_id.use_brand_description_sale = True
        self.product_consu_a.brand_id.description_sale = "Price : {{ object.list_price }}"
        self.assertEqual(
            self.sale_order_template_1.sale_order_template_line_ids[0].name,
            # get from product.template._recompute_product_name()
            "[BA_PCA_123] Brand A - Product Consu A\nPrice : 100.0",
        )

    def test_02_update_product_product_values_ok(self):
        """Test update of product values. Product name is updated because it has not been manually updated"""
        self.product_consu_a.name = "Updated product name"
        self.assertEqual(
            self.sale_order_template_1.sale_order_template_line_ids[0].name,
            # get from product.template._recompute_product_name()
            "[BA_PCA_123] Brand A - Updated product name\nBrand A Description\nProduct : Updated product name",
        )

    def test_03_update_product_product_values_nok(self):
        """Test update of product values. Product name is not updated because it has been manually updated"""
        self.sale_order_template_1.sale_order_template_line_ids[0].name = "Updated line name"
        self.product_consu_a.name = "Updated product name"
        self.assertEqual(self.sale_order_template_1.sale_order_template_line_ids[0].name, "Updated line name")
