# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_base.tests.common import TestOFBaseCommon


class TestOFProductCommon(TestOFBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Product data
        cls.product_category_a = (
            cls.env['product.category']
            .with_company(cls.company_fr)
            .create(
                {
                    'name': 'Category A',
                }
            )
        )
