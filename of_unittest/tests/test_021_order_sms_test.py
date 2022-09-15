# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
import datetime
from odoo.addons.of_unittest.tests.test_order_common import OFTestOrderTransactionCase


class OFTestOrder(OFTestOrderTransactionCase):

    def test_02_create_and_confirm_order_sms_test_ok(self):
        """ Test de création d'une commande.
        1 - Je crée une commande avec un client et une ligne de commande.
        2 - Je vérifie que la commande a bien été créée
        3 - Je crée une ligne de commande avec un produit et une quantité de 1 et un prix de vente de 150€
        4 - Je vérifie que la ligne de commande a bien été créée
            - La quantité doit être de 1
            - Le sous total de la ligne doit être de 150€
        5 - Je contrôle les montants de la commande
        6 - Je confirme la commande
            - Attention nous ne voulons pas contacter le service externe
            - On souhaite quand même vérifier l'appel à la méthode d'envoi au service externe
                - Elle ne doit être appelée qu'une seule fois
        7 - Le client doit changer de statut
        8 - Je souhaite tester l'envoi de sms à l'utilisateur en fonction du jour de la semaine
            - Pendant la semaine le SMS est envoyé
            - Le weekend le SMS n'est pas envoyé"""
        sale_order_obj = self.env['sale.order']
        sale_order_line_obj = self.env['sale.order.line']

        # Sale order creation
        order_values = sale_order_obj.default_get(sale_order_obj.fields_get().keys())
        order_values.update({
            'partner_id': self.test_partner.id,
        })
        test_order = sale_order_obj.create(order_values)
        test_order.onchange_partner_id()
        self.assertNotEqual(test_order, sale_order_obj)
        self.assertEqual(test_order.partner_id.name, 'Jean-michel Voixdechiotte')
        self.assertEqual(test_order.partner_shipping_id.name, 'Livraison')
        self.assertEqual(test_order.partner_invoice_id.name, 'Facturation')

        # Order line creation
        line_values = sale_order_line_obj.default_get(sale_order_line_obj.fields_get().keys())
        line_values.update({
            'order_id': test_order.id,
            'product_id': self.test_product.id,
            'product_uom_qty': 1,
            'price_unit': 150,
        })
        test_order_line = sale_order_line_obj.create(line_values)
        test_order_line.product_id_change()
        self.assertEqual(test_order.order_line[0].product_id, self.test_product)
        self.assertEqual(test_order.order_line[0].product_id.name, 'Test Product')
        self.assertEqual(test_order.order_line[0].product_uom_qty, 1)
        self.assertEqual(test_order.state, 'sent')

        # Order confirmation and test SMS sending OK
        with mock.patch.object(test_order, '_send_sale_to_external_service') as m:
            with mock.patch('odoo.addons.of_unittest.models.sale.datetime') as mock_date:
                mock_date.now.return_value = datetime.date(2022, 9, 12)  # It's Monday
                mock_date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
                test_order.action_confirm()
                m.assert_called_once()

        self.assertEqual(test_order.state, 'sale')
        self.assertEqual(test_order.weekday_sms_sent, True)

        # Customer type change
        self.assertEqual(self.test_partner.of_customer_state, 'customer')

    def test_03_create_and_confirm_order_sms_test_nok(self):
        """ Test de création d'une commande.
        1 - Je crée une commande avec un client et une ligne de commande.
        2 - Je vérifie que la commande a bien été créée
        3 - Je crée une ligne de commande avec un produit et une quantité de 1 et un prix de vente de 150€
        4 - Je vérifie que la ligne de commande a bien été créée
            - La quantité doit être de 1
            - Le sous total de la ligne doit être de 150€
        5 - Je contrôle les montants de la commande
        6 - Je confirme la commande
            - Attention nous ne voulons pas contacter le service externe
            - On souhaite quand même vérifier l'appel à la méthode d'envoi au service externe
                - Elle ne doit être appelée qu'une seule fois
        7 - Le client doit changer de statut
        8 - Je souhaite tester l'envoi de sms à l'utilisateur en fonction du jour de la semaine
            - Pendant la semaine le SMS est envoyé
            - Le weekend le SMS n'est pas envoyé"""
        sale_order_obj = self.env['sale.order']
        sale_order_line_obj = self.env['sale.order.line']

        # Sale order creation
        order_values = sale_order_obj.default_get(sale_order_obj.fields_get().keys())
        order_values.update({
            'partner_id': self.test_partner.id,
        })
        test_order = sale_order_obj.create(order_values)
        test_order.onchange_partner_id()
        self.assertNotEqual(test_order, sale_order_obj)
        self.assertEqual(test_order.partner_id.name, 'Jean-michel Voixdechiotte')
        self.assertEqual(test_order.partner_shipping_id.name, 'Livraison')
        self.assertEqual(test_order.partner_invoice_id.name, 'Facturation')

        # Order line creation
        line_values = sale_order_line_obj.default_get(sale_order_line_obj.fields_get().keys())
        line_values.update({
            'order_id': test_order.id,
            'product_id': self.test_product.id,
            'product_uom_qty': 1,
            'price_unit': 150,
        })
        test_order_line = sale_order_line_obj.create(line_values)
        test_order_line.product_id_change()
        self.assertEqual(test_order.order_line[0].product_id, self.test_product)
        self.assertEqual(test_order.order_line[0].product_id.name, 'Test Product')
        self.assertEqual(test_order.order_line[0].product_uom_qty, 1)
        self.assertEqual(test_order.state, 'sent')

        # Order confirmation and test SMS sending OK
        with mock.patch.object(test_order, '_send_sale_to_external_service') as m:
            with mock.patch('odoo.addons.of_unittest.models.sale.datetime') as mock_date:
                mock_date.now.return_value = datetime.date(2022, 9, 18)  # It's Sunday
                mock_date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
                test_order.action_confirm()
                m.assert_called_once()

        self.assertEqual(test_order.state, 'sale')
        self.assertEqual(test_order.weekday_sms_sent, False)

        # Customer type change
        self.assertEqual(self.test_partner.of_customer_state, 'customer')
