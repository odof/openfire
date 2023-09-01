# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSalePartnerWarning(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_with_warning = cls.env['res.partner'].create(
            {
                'name': 'Partner with warning',
                'of_is_sale_warn': True,
                'invoice_warn_msg': 'This is a warning message',
            }
        )

    def test_01_no_partner_warning(self):
        order_values = self._prepare_empty_sale_order_values()
        order = self.env['sale.order'].create(order_values)
        res = order._onchange_partner_id_warning()
        self.assertEqual(res, None)

    def test_02_partner_warning(self):
        order_values = self._prepare_empty_sale_order_values()
        order_values['partner_id'] = self.partner_with_warning.id
        order = self.env['sale.order'].create(order_values)
        res = order._onchange_partner_id_warning()
        self.assertEqual(res['warning']['message'], 'This is a warning message')

    def test_03_partner_blocking_warning(self):
        self.partner_with_warning.of_warn_block = True
        order_values = self._prepare_empty_sale_order_values()
        order_values['partner_id'] = self.partner_with_warning.id
        order = self.env['sale.order'].create(order_values)
        res = order._onchange_partner_id_warning()
        self.assertEqual(res['warning']['message'], 'This is a warning message')
        self.assertEqual(order.partner_id, self.env['res.partner'].browse())
