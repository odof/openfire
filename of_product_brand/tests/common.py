# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_product.tests.common import TestOFProductCommon


class TestOFProductCommon(TestOFProductCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Brand data
        cls.product_brand_a = (
            cls.env["of.product.brand"]
            .with_company(cls.company_fr)
            .create(
                {
                    "name": "Brand A",
                    "code": "BA",
                    "partner_id": cls.supplier_a.id,
                    "use_brand_description_sale": True,
                    "description_sale": "Brand A Description\nProduct : {{object.name}}",
                    "show_in_sales": True,
                }
            )
        )
        cls.product_brand_b = (
            cls.env["of.product.brand"]
            .with_company(cls.company_fr)
            .create(
                {
                    "name": "Brand B",
                    "code": "BB",
                    "partner_id": cls.supplier_b.id,
                    "use_brand_description_sale": False,
                    "description_sale": "Brand B Description\nProduct : {{object.name}}",
                    "show_in_sales": True,
                }
            )
        )
        cls.product_brand_c = (
            cls.env["of.product.brand"]
            .with_company(cls.company_fr)
            .create(
                {
                    "name": "Brand C",
                    "code": "BC",
                    "partner_id": cls.supplier_a.id,
                    "use_brand_description_sale": False,
                    "description_sale": False,
                    "show_in_sales": False,
                }
            )
        )
