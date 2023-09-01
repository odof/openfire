# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFLockedOrderLine(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Product & category data
        cls.deposit_category = cls.env['product.category'].create({'name': 'Deposit category'})
        cls.deposit_product = cls.create_product(
            {
                'name': 'Deposit product',
                'default_code': 'BA_DEPOSIT',
                'standard_price': 0,
                'list_price': 1,
                'categ_id': cls.deposit_category.id,
                'type': 'service',
            }
        )
        cls.locked_category = cls.env['product.category'].create({'name': 'Locked category'})

    def test_01_of_locked_order_line(self):
        """Test that the order line is locked when the product is in a locked category.
        We can't modify some fields of the order line when it is locked.
        """
        # Set the locked category
        self.env['res.config.settings'].create(
            {
                'of_deposit_product_categ_id': self.deposit_category.id,
            }
        ).execute()

        # Create order
        order_values = self._prepare_empty_sale_order_values()
        order_values['order_line'] = [
            Command.create(
                {
                    'product_id': self.product_consu_a.id,
                    'product_uom_qty': 1,
                    'price_unit': 500,
                }
            ),
        ]
        order = self.env['sale.order'].create(order_values)

        # Generate deposit invoice
        order.action_verification_confirm()
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_ids=[order.id])
            .create(
                {
                    'advance_payment_method': 'fixed',
                    'fixed_amount': 150,
                }
            )
        )
        wizard.create_invoices()
        self.assertEqual(len(order.invoice_ids), 1)

        # Check that the order line is locked
        invoice = order.invoice_ids[0]
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids[0].product_id, self.deposit_product)
        self.assertTrue(invoice.invoice_line_ids[0].of_is_locked, True)

        # Try to modify the order line when it is locked. It should raise an error.
        deposit_line = order.order_line.filtered(lambda line: line.product_id == self.deposit_product)
        with self.assertRaises(UserError):
            deposit_line.product_uom_qty = 2

        # Try to modify a non locked field. It should not raise an error.
        deposit_line.name = f"{deposit_line.name} test"

    def test_02_sync_sale_order_line_fields(self):
        """Test that the fields of the account move line are synchronized with the sale order line when the
        account move line is locked."""
        # Set the locked category
        self.env['res.config.settings'].create(
            {
                'of_deposit_product_categ_id': self.deposit_category.id,
            }
        ).execute()

        # Create order
        order_values = self._prepare_empty_sale_order_values()
        order_values['order_line'] = [
            Command.create(
                {
                    'product_id': self.product_consu_a.id,
                    'product_uom_qty': 1,
                    'price_unit': 500,
                }
            ),
        ]
        order = self.env['sale.order'].create(order_values)

        # Generate deposit invoice
        order.action_verification_confirm()
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_ids=[order.id])
            .create(
                {
                    'advance_payment_method': 'fixed',
                    'fixed_amount': 150,
                }
            )
        )
        wizard.create_invoices()
        self.assertEqual(len(order.invoice_ids), 1)

        # Check that the order line is locked
        invoice = order.invoice_ids[0]
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids[0].product_id, self.deposit_product)
        self.assertTrue(invoice.invoice_line_ids[0].of_is_locked, True)

        # Modify the account move line
        invoice.invoice_line_ids[0].price_unit = 250

        # Check that the sale order line is synchronized
        deposit_line = order.order_line.filtered(lambda line: line.product_id == self.deposit_product)
        self.assertEqual(deposit_line.price_unit, 250)
