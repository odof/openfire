# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_account.tests.common import TestOFAccountCommon
from odoo.addons.of_dms.tests.common import TestOFDMSCommon

from ..hooks import post_init_hook


class TestOFDMSAccountCommon(TestOFDMSCommon, TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        post_init_hook(cls.cr, cls.env)

        cls.brand_stove = cls.env["of.product.brand"].create(
            {
                "name": "Stove Brand 1",
                "code": "SB1",
                "partner_id": cls.supplier_b.id,
            }
        )

        cls.product_wood_stove = cls.env["product.product"].create(
            {
                "name": "Poêle à bois",
                "type": "product",
                "list_price": 1000,
                "brand_id": cls.brand_stove.id,
                "description_sale": "Superbe Poêle à bois de marque Stove Brand 1",
            }
        )

        cls.account_directories = (
            cls.directory_model.with_context({"active_test": False})
            .search(
                [
                    ("res_model", "=", "account.move"),
                    (
                        "parent_id",
                        "in",
                        [
                            cls.customer_a.of_dms_directory_id.id,
                            cls.supplier_a.of_dms_directory_id.id,
                            cls.supplier_b.of_dms_directory_id.id,
                        ],
                    ),
                ]
            )
            .sorted("id")
        )
