# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, fields
from odoo.tests import Form

from odoo.addons.account.tests.test_account_move_in_invoice import TestAccountMoveInInvoiceOnchanges


class TestOFAccountMovePaymentSchedule(TestAccountMoveInInvoiceOnchanges):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Payment terms data
        cls.payment_term_15days = (
            cls.env['account.payment.term']
            .with_company(cls.company_fr)
            .create(
                {
                    'name': '15 days',
                    'line_ids': [
                        Command.create({'of_name': '15 days', 'value': 'balance', 'days': 15}),
                    ],
                }
            )
        )
        cls.payment_term_30_30_40 = (
            cls.env['account.payment.term']
            .with_company(cls.company_fr)
            .create(
                {
                    'name': '30% à la facture, 30% à la livraison, Solde 40%',
                    'line_ids': [
                        Command.create(
                            {'of_name': '30% à la facture', 'value': 'percent', 'value_amount': 30.0, 'days': 1}
                        ),
                        Command.create(
                            {'of_name': '30% à la livraison', 'value': 'percent', 'value_amount': 30.0, 'days': 8}
                        ),
                        Command.create({'of_name': 'Solde 40%', 'value': 'balance', 'days': 15}),
                    ],
                }
            )
        )

        cls.move_vals = {
            'partner_id': cls.partner_a.id,
            'currency_id': cls.company_data['currency'].id,
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'date': fields.Date.from_string('2019-01-01'),
            'fiscal_position_id': False,
            'payment_reference': '',
            'invoice_payment_term_id': cls.payment_term_30_30_40.id,
            'amount_untaxed': 960.0,
            'amount_tax': 168.0,
            'amount_total': 1128.0,
            'invoice_line_ids': [
                Command.create(
                    {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 960.0,
                        'tax_ids': [(6, 0, [cls.company_data['default_tax_sale'].id])],
                    }
                )
            ],
        }

    def test_01_payment_schedule_creation(self):
        """Test Payment Schedule creation depending on the payment term."""
        invoice = self.env['account.move'].create(self.move_vals)
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.of_payment_schedule_ids[0].name, '30% à la facture')
        self.assertEqual(invoice.of_payment_schedule_ids[1].name, '30% à la livraison')
        self.assertEqual(invoice.of_payment_schedule_ids[2].name, 'Solde 40%')

    def test_02_payment_schedule_update(self):
        """Test Payment Schedule update when the payment term is changed."""
        invoice = self.env['account.move'].create(self.move_vals)
        invoice.payment_term_id = self.payment_term_15days
        invoice._compute_of_payment_schedule_ids()
        self.assertEqual(len(invoice.of_payment_schedule_ids), 1)
        self.assertEqual(invoice.of_payment_schedule_ids[0].name, '15 days')
        invoice.payment_term_id = self.payment_term_30_30_40
        invoice._compute_of_payment_schedule_ids()
        self.assertEqual(len(invoice.of_payment_schedule_ids), 3)
        self.assertEqual(invoice.of_payment_schedule_ids[0].name, '30% à la facture')
        self.assertEqual(invoice.of_payment_schedule_ids[1].name, '30% à la livraison')
        self.assertEqual(invoice.of_payment_schedule_ids[2].name, 'Solde 40%')

    def test_03_payment_schedule_percent_update(self):
        """Test that the amount is updated when the percentage is changed"""

        invoice = self.env['account.move'].create(self.move_vals)
        self.assertEqual(len(invoice.of_payment_schedule_ids), 3)
        with Form(invoice) as invoice_form:
            with self.assertRaisesRegex(AssertionError, "can't write on readonly field percent"):
                with invoice_form.of_payment_schedule_ids.edit(2) as payment_line_form:
                    # we can't update the last payment, that a read only field
                    payment_line_form.percent = 50
            with invoice_form.of_payment_schedule_ids.edit(0) as payment_line_form:
                payment_line_form.percent = 20
            self.assertEqual(payment_line_form.amount, 21.1)

    def test_04_payment_schedule_amount_update(self):
        """Test that the percentage is updated when the amount is changed"""
        invoice = self.env['account.move'].create(self.move_vals)

        self.assertEqual(len(invoice.of_payment_schedule_ids), 3)
        with Form(invoice) as invoice_form:
            with self.assertRaisesRegex(AssertionError, "can't write on readonly field percent"):
                with invoice_form.of_payment_schedule_ids.edit(2) as payment_line_form:
                    # we can't update the last payment, that a read only field
                    payment_line_form.percent = 50

            with invoice_form.of_payment_schedule_ids.edit(0) as payment_line_form:
                payment_line_form.amount = 21.1
            self.assertEqual(payment_line_form.percent, 20)
