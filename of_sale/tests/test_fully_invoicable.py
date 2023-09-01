# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleFullyInvoicable(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_fully_invoicable_order(self):
        """Test that the order is fully invoicable if :
        - the order is confirmed
        - the order is confirmer and emtpy
        - the invoice is created and posted (FIXME?)
        """
        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        self.assertFalse(order.of_fully_invoicable)
        order.action_verification_confirm()
        self.assertTrue(order.of_fully_invoicable)

        order2 = self.env['sale.order'].create(self._prepare_empty_sale_order_values())
        self.assertFalse(order2.of_fully_invoicable)
        order2.action_verification_confirm()
        self.assertTrue(order2.of_fully_invoicable)

        order_values = self._prepare_sale_order_values()
        order_values['of_invoice_policy'] = 'order'
        order3 = self.env['sale.order'].create(order_values)
        self.assertFalse(order3.of_fully_invoicable)
        order3.action_verification_confirm()
        self.env['sale.advance.payment.inv'].with_context(active_ids=[order3.id]).create(
            {
                'advance_payment_method': 'delivered',
            }
        ).create_invoices()
        self.assertEqual(len(order3.invoice_ids), 1)
        self.assertEqual(order3.invoice_status, 'invoiced')
        self.assertTrue(order3.of_fully_invoicable)
        order3.invoice_ids[0].action_post()
        # An Order still invoicable even if the invoice is created and posted, that's weird
        self.assertTrue(order3.of_fully_invoicable)

    def test_02_not_fully_invoicable_order(self):
        """Test that the order is not fully invoicable if :
        - the order is not confirmed
        - the invoice status is forced to 'invoiced'
        - the invoice status is forced to 'no'"""

        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        self.assertFalse(order.of_fully_invoicable)

        order.of_force_invoice_status = 'invoiced'
        order.action_verification_confirm()
        self.assertFalse(order.of_fully_invoicable)

        order3 = self.env['sale.order'].create(self._prepare_sale_order_values())
        self.assertFalse(order3.of_fully_invoicable)
        order3.of_force_invoice_status = 'no'
        order3.action_verification_confirm()
        self.assertFalse(order3.of_fully_invoicable)
