# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFProductStandardCommon(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_standard = cls.env["of.product.standard"].create(
            {
                "code": "S1",
                "name": "Standard 1",
                "description": "This is the standard 1",
            }
        )
        cls.product_standard2 = cls.env["of.product.standard"].create(
            {
                "code": "S2",
                "name": "Standard 2",
                "description": "This is the standard 2",
            }
        )
