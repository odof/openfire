# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
import datetime
from odoo.addons.of_unittest.tests.test_order_common import OFAdvancedTestOrderTransactionCase
from odoo.addons.of_unittest.tests.test_account_common import OFTestAccountTransactionCase
from odoo import fields

 # always mock requests so as to not make call to APIs
@mock.patch('requests.request')
@mock.patch('requests.get')
@mock.patch('requests.post')
@mock.patch('requests.patch')
@mock.patch('requests.put')
@mock.patch('requests.delete')
@mock.patch('requests.head')
@mock.patch('requests.options')
class OFTestOrder(OFAdvancedTestOrderTransactionCase, OFTestAccountTransactionCase):

    def test_03_invoicing_order(self, *args):
        """ Test de création d'une facture
        1 - Génération de la facture depuis la commande
        """
        sale_advance_payment_inv_obj = self.env['sale.advance.payment.inv']
        test_order = self.test_order

        # on confirme la commande et on vérifie qu'on est passé a l'état sale
        test_order.action_confirm()
        self.assertEqual(test_order.state, 'sale')
        # test de création de la facture
        invoicing_wizard_vals = {
            'advance_payment_method': 'all',
        }
        wizard = sale_advance_payment_inv_obj.with_context(active_ids=[test_order.id]).create(invoicing_wizard_vals)
        wizard.create_invoices()
        # la facture est bien créée
        self.assertGreater(len(test_order.invoice_ids), 0)
        test_order.invoice_ids.action_invoice_open()
        self.assertEqual(test_order.invoice_ids[0].state, 'open')


    def test_04_add_payment_to_order(self, *args):
        """ Test de création d'un paiement attaché à une commande.
        1 - Un paiement doit être généré depuis la commande
        """
        account_payment_obj = self.env['account.payment']
        test_order = self.test_order

        # on confirme la commande et on vérifie qu'on est passé a l'état sale
        test_order.action_confirm()
        self.assertEqual(test_order.state, 'sale')
        # test de création du paiement
        account_payment_vals = {
            'order_ids': [(4, test_order.id, None)],
            'amount': test_order.amount_total,
            'payment_date': fields.Date.today(),
            'partner_id': self.test_partner.id,
            'partner_type': 'customer' if self.test_partner.customer else 'supplier',
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'payment_difference_handling': 'open',
            'writeoff_account_id': False,
            'communication': '',
            'of_payment_mode_id': self.test_mode_payment.id,
        }
        payment = account_payment_obj.create(account_payment_vals)
        payment.post()
        # le paiement est bien créé
        self.assertGreater(len(test_order.payment_ids), 0)
        self.assertEqual(payment.state, 'posted')

    def test_05_pay_order_invoice(self, *args):
        sale_advance_payment_inv_obj = self.env['sale.advance.payment.inv']
        account_payment_obj = self.env['account.payment']
        test_order = self.test_order

        # on confirme la commande et on vérifie qu'on est passé a l'état sale
        test_order.action_confirm()
        self.assertEqual(test_order.state, 'sale')
        # test de création de la facture
        invoicing_wizard_vals = {
            'advance_payment_method': 'all',
        }
        wizard = sale_advance_payment_inv_obj.with_context(active_ids=[test_order.id]).create(invoicing_wizard_vals)
        wizard.create_invoices()
        # la facture est bien créée
        self.assertGreater(len(test_order.invoice_ids), 0)
        test_order.invoice_ids.action_invoice_open()
        self.assertEqual(test_order.invoice_ids[0].state, 'open')
        # test de création du paiement
        account_payment_vals = {
            'order_ids': [(4, test_order.id, None)],
            'amount': test_order.amount_total,
            'payment_date': fields.Date.today(),
            'partner_id': self.test_partner.id,
            'partner_type': 'customer' if self.test_partner.customer else 'supplier',
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'payment_difference_handling': 'open',
            'writeoff_account_id': False,
            'communication': '',
            'of_payment_mode_id': self.test_mode_payment.id,
        }
        payment = account_payment_obj.create(account_payment_vals)
        payment.post()
        # le paiement est bien créé
        self.assertGreater(len(test_order.payment_ids), 0)
        # self.assertEqual(payment.state, 'posted')
        # on fait le lettrage
        self.assertEqual(test_order.invoice_ids[0].amount_total, payment.amount)
        lines = payment.move_line_ids.filtered(
            lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        test_order.invoice_ids[0].register_payment(lines)
        # la facture doit maintenant être payée
        self.assertEqual(test_order.invoice_ids[0].state, 'paid')
