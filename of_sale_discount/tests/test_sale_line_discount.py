# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestSaleOrderLine(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.order = cls.env['sale.order'].create(cls._prepare_sale_order_values(cls))
        cls.first_order_line = cls.order.order_line[0]

    def test_01_of_discount_formula(self):
        """Test that the field standard field discount is correctly computed from the field of_discount_formula"""
        self.first_order_line.of_discount_formula = '10'
        self.assertEqual(self.first_order_line.discount, 10.0)

        self.first_order_line.of_discount_formula = '10 + 5'
        self.assertEqual(self.first_order_line.discount, 14.5)

        self.first_order_line.of_discount_formula = '10,5'
        self.assertEqual(self.first_order_line.discount, 10.5)

        with self.assertRaises(Exception):
            self.first_order_line.of_discount_formula = '10 + abc'

    def test_02_create_order_line(self):
        """Test that both fields discount and of_discount_formula are correctly computed during the creation of a
        sale order line"""
        sale_order_line1 = self.env['sale.order.line'].create(
            {
                'order_id': self.order.id,
                'product_id': self.product_consu_a.id,
                'product_uom_qty': 1.0,
                'price_unit': 100.0,
                'discount': 10.0,
            }
        )
        self.assertEqual(sale_order_line1.of_discount_formula, '10.0')

        sale_order_line2 = self.env['sale.order.line'].create(
            {
                'order_id': self.order.id,
                'product_id': self.product_consu_a.id,
                'product_uom_qty': 1.0,
                'price_unit': 100.0,
                'of_discount_formula': '10.0',
            }
        )
        self.assertEqual(sale_order_line2.discount, 10.0)

    def test_03_write_order_line(self):
        """Test that both fields discount and of_discount_formula are correctly computed during the write of a
        sale order line"""
        self.first_order_line.write(
            {
                'discount': 10.0,
            }
        )
        self.assertEqual(self.first_order_line.of_discount_formula, '10.0')

        self.first_order_line.write(
            {
                'of_discount_formula': '11.0',
            }
        )
        self.assertEqual(self.first_order_line.discount, 11.0)

    def test_04_blocked_fields_on_write(self):
        """Test that the field of_discount_formula is a part of the blocked fields on write"""
        self.assertIn('of_discount_formula', self.first_order_line._get_blocked_fields_on_write())

    def test_05_prepare_invoice_line(self):
        """Test that the value of of_discount_formula is correctly copied to the invoice line values"""
        invoice_line = self.first_order_line._prepare_invoice_line()
        self.assertEqual(invoice_line['of_discount_formula'], self.first_order_line.of_discount_formula)

    def test_06_create_invoice(self):
        """Test that the field of_discount_formula is correctly copied to the invoice line when the invoice is
        created"""
        self.order.action_verification_confirm()
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_ids=[self.order.id])
            .create(
                {
                    'advance_payment_method': 'delivered',
                }
            )
        )
        wizard.create_invoices()
        self.assertEqual(len(self.order.invoice_ids), 1)
        self.assertEqual(
            self.order.invoice_ids.invoice_line_ids[0].of_discount_formula, self.first_order_line.of_discount_formula
        )
