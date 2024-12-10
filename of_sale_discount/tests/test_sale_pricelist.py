# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import Form

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSalePriceListCustom(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.config.settings"].create({"group_sale_pricelist": True}).execute()

        cls.categ_stove = cls.env["product.category"].create(
            {"parent_id": cls.env.ref("product.product_category_all").id, "name": "Stove"}
        )
        cls.categ_misc = cls.env["product.category"].create(
            {"parent_id": cls.env.ref("product.product_category_all").id, "name": "Misc"}
        )
        cls.brand_supplier_stove = cls.env["of.product.brand"].create(
            {"name": "Stove supplier brand", "code": "STO", "partner_id": cls.supplier_a.id}
        )
        cls.brand_company = cls.env["of.product.brand"].create(
            {"name": "My company", "code": "MY", "partner_id": cls.company_fr.partner_id.id}
        )

        cls.pricelist_discount = cls.env["product.pricelist"].create(
            {
                "name": "Discount on brand/categs",
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "percentage",
                            "applied_on": "2_product_category",
                            "percent_price": 10,
                            "of_categ_ids": [Command.set((cls.categ_stove + cls.categ_misc).ids)],
                            "of_brand_ids": [Command.set(cls.brand_supplier_stove.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "compute_price": "percentage",
                            "applied_on": "2_product_category",
                            "percent_price": 5,
                            "of_categ_ids": [Command.set(cls.categ_misc.ids)],
                            "of_brand_ids": [Command.set(cls.brand_company.ids)],
                        }
                    ),
                ],
            }
        )

        cls.product_test1 = cls.env["product.product"].create(
            {
                "name": "Product test 1",
                "categ_id": cls.categ_stove.id,
                "brand_id": cls.brand_supplier_stove.id,
                "list_price": 1500,
            }
        )

        cls.product_test2 = cls.env["product.product"].create(
            {
                "name": "Product test 2",
                "categ_id": cls.categ_misc.id,
                "brand_id": cls.brand_supplier_stove.id,
                "list_price": 1515,
            }
        )

        cls.product_test3 = cls.env["product.product"].create(
            {
                "name": "Product test 3",
                "categ_id": cls.categ_misc.id,
                "brand_id": cls.brand_company.id,
                "list_price": 500,
            }
        )

        cls.product_test4 = cls.env["product.product"].create(
            {
                "name": "Product test 4",
                "categ_id": cls.env.ref("product.product_category_all").id,
                "brand_id": cls.brand_company.id,
                "list_price": 400,
            }
        )

    def test_01_pricelist_item_names(self):
        self.assertEqual(self.pricelist_discount.item_ids[0].name, "Catégorie(s) : All / Stove, All / Misc")
        self.assertEqual(self.pricelist_discount.item_ids[1].name, "Catégorie(s) : All / Misc")

    def test_02_order_pricelist(self):
        """Test custom modification of pricelist item, to allow management of many categories and brands"""
        with Form(self.env["sale.order"].create(self._prepare_empty_sale_order_values())) as order_form:
            order_form.pricelist_id = self.pricelist_discount
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.product_test1
            with order_form.order_line.new() as line_form2:
                line_form2.product_id = self.product_test2
            with order_form.order_line.new() as line_form3:
                line_form3.product_id = self.product_test3
            with order_form.order_line.new() as line_form4:
                line_form4.product_id = self.product_test4
            order = order_form.save()
        self.assertRecordValues(
            order.order_line,
            [
                {"product_id": self.product_test1.id, "price_unit": 1350.0},
                {"product_id": self.product_test2.id, "price_unit": 1363.5},
                {"product_id": self.product_test3.id, "price_unit": 475.0},
                {"product_id": self.product_test4.id, "price_unit": 400.0},
            ],
        )
