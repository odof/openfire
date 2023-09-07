# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests import Form

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleOrderPaymentSchedule(TestOFSaleCommon):
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
                    'name': '30% à la commande, 30% à la livraison, Solde 40%',
                    'line_ids': [
                        Command.create(
                            {'of_name': '30% à la commande', 'value': 'percent', 'value_amount': 30.0, 'days': 1}
                        ),
                        Command.create(
                            {'of_name': '30% à la livraison', 'value': 'percent', 'value_amount': 30.0, 'days': 8}
                        ),
                        Command.create({'of_name': 'Solde 40%', 'value': 'balance', 'days': 15}),
                    ],
                }
            )
        )

    def test_01_payment_schedule_creation(self):
        """Test Payment Schedule creation depending on the payment term."""
        order_values = self._prepare_sale_order_values(price_unit=100)
        order_values['payment_term_id'] = self.payment_term_30_30_40.id
        sale_order = self.env['sale.order'].create(order_values)
        self.assertEqual(sale_order.amount_untaxed, 100.0)
        self.assertEqual(sale_order.amount_tax, 5.5)
        self.assertEqual(sale_order.amount_total, 105.5)
        self.assertEqual(len(sale_order.of_payment_schedule_ids), 3)
        self.assertEqual(sale_order.of_payment_schedule_ids[0].name, '30% à la commande')
        self.assertEqual(
            sale_order.of_payment_schedule_ids[0].date, sale_order.date_order.date() + relativedelta(days=1)
        )
        self.assertEqual(sale_order.of_payment_schedule_ids[1].name, '30% à la livraison')
        self.assertEqual(
            sale_order.of_payment_schedule_ids[1].date, sale_order.date_order.date() + relativedelta(days=8)
        )
        self.assertEqual(sale_order.of_payment_schedule_ids[2].name, 'Solde 40%')
        self.assertEqual(
            sale_order.of_payment_schedule_ids[2].date, sale_order.date_order.date() + relativedelta(days=15)
        )
        self.assertEqual(sum(sale_order.of_payment_schedule_ids.mapped('amount')), 105.5)

    def test_02_payment_schedule_update(self):
        """Test Payment Schedule update when the payment term is changed."""
        order_values = self._prepare_sale_order_values(price_unit=100)
        sale_order = self.env['sale.order'].new(order_values)
        sale_order.payment_term_id = self.payment_term_15days
        sale_order._compute_of_payment_schedule_ids()
        self.assertEqual(len(sale_order.of_payment_schedule_ids), 1)
        self.assertEqual(sale_order.of_payment_schedule_ids[0].name, '15 days')
        self.assertEqual(sale_order.of_payment_schedule_ids[0].amount, 105.5)
        self.assertEqual(
            sale_order.of_payment_schedule_ids[0].date, sale_order.date_order.date() + relativedelta(days=15)
        )
        sale_order.payment_term_id = self.payment_term_30_30_40
        sale_order._compute_of_payment_schedule_ids()
        self.assertEqual(len(sale_order.of_payment_schedule_ids), 3)
        self.assertEqual(sale_order.of_payment_schedule_ids[0].name, '30% à la commande')
        self.assertEqual(
            sale_order.of_payment_schedule_ids[0].date, sale_order.date_order.date() + relativedelta(days=1)
        )
        self.assertEqual(sale_order.of_payment_schedule_ids[1].name, '30% à la livraison')
        self.assertEqual(
            sale_order.of_payment_schedule_ids[1].date, sale_order.date_order.date() + relativedelta(days=8)
        )
        self.assertEqual(sale_order.of_payment_schedule_ids[2].name, 'Solde 40%')
        self.assertEqual(
            sale_order.of_payment_schedule_ids[2].date, sale_order.date_order.date() + relativedelta(days=15)
        )
        self.assertEqual(sum(sale_order.of_payment_schedule_ids.mapped('amount')), 105.5)

    def test_03_payment_schedule_percent_update(self):
        """Test that the amount is updated when the percentage is changed"""
        order_values = self._prepare_sale_order_values(price_unit=100)
        order_values['payment_term_id'] = self.payment_term_30_30_40.id
        sale_order = self.env['sale.order'].create(order_values)

        self.assertEqual(len(sale_order.of_payment_schedule_ids), 3)

        with Form(sale_order) as order_form:
            with self.assertRaisesRegex(AssertionError, "can't write on readonly field percent"):
                with order_form.of_payment_schedule_ids.edit(2) as payment_line_form:
                    # we can't update the last payment, that a read only field
                    payment_line_form.percent = 50

            with order_form.of_payment_schedule_ids.edit(0) as payment_line_form:
                payment_line_form.percent = 20

            self.assertEqual(payment_line_form.amount, 21.1)

    def test_04_payment_schedule_amount_update(self):
        """Test that the percentage is updated when the amount is changed"""
        order_values = self._prepare_sale_order_values(price_unit=100)
        order_values['payment_term_id'] = self.payment_term_30_30_40.id
        sale_order = self.env['sale.order'].create(order_values)

        self.assertEqual(len(sale_order.of_payment_schedule_ids), 3)

        with Form(sale_order) as order_form:
            with self.assertRaisesRegex(AssertionError, "can't write on readonly field percent"):
                with order_form.of_payment_schedule_ids.edit(2) as payment_line_form:
                    # we can't update the last payment, that a read only field
                    payment_line_form.percent = 50

            with order_form.of_payment_schedule_ids.edit(0) as payment_line_form:
                payment_line_form.amount = 21.1

            self.assertEqual(payment_line_form.percent, 20)
