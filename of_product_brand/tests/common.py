# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'openfire_custom')
class TestOFProductCommon(TransactionCase):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_supplier = cls.env['res.partner'].create({'name': 'Test Supplier', 'supplier_rank': 1})
        cls.another_supplier = cls.env['res.partner'].create({'name': 'Other Supplier', 'supplier_rank': 1})
        cls.test_brand = cls.env['of.product.brand'].create(
            {'name': "Test Brand", 'code': 'TB', 'partner_id': cls.test_supplier.id}
        )
        cls.another_brand = cls.env['of.product.brand'].create(
            {'name': "Other Brand", 'code': 'OB', 'partner_id': cls.another_supplier.id}
        )
