# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import mock
from odoo.addons.of_unittest.tests.test_order_common import OFTestOrderTransactionCase

 # always mock requests so as to not make call to APIs
@mock.patch('requests.request')
@mock.patch('requests.get')
@mock.patch('requests.post')
@mock.patch('requests.patch')
@mock.patch('requests.put')
@mock.patch('requests.delete')
@mock.patch('requests.head')
@mock.patch('requests.options')
class OFTestOrder(OFTestOrderTransactionCase):

    def test_00_create_order(self, *args):
        """ Test de création d'une commande.
        1 - Je crée une commande avec un client et une ligne de commande.
        2 - Je vérifie que la commande a bien été créée
        3 - Je crée une ligne de commande avec un produit et une quantité de 2
        4 - Je vérifie que la ligne de commande a bien été créée et que le prix de vente est bien celui du produit
            - Le prix de vente doit être de 100€
            - La quantité doit être de 2
            - Le sous total de la ligne doit être de 200€
        5 - Je contrôle les montants de la commande
        6 - Le client doit changer de statut"""
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
        self.assertEqual(test_order.partner_id.name, 'Jean-michel client')
        self.assertEqual(test_order.partner_shipping_id.name, 'Livraison')
        self.assertEqual(test_order.partner_invoice_id.name, 'Facturation')

        # Order line creation
        line_values = sale_order_line_obj.default_get(sale_order_line_obj.fields_get().keys())
        line_values.update({
            'order_id': test_order.id,
            'product_id': self.test_product.id,
            'product_uom_qty': 2,
        })
        test_order_line = sale_order_line_obj.create(line_values)
        test_order_line.product_id_change()
        self.assertEqual(test_order.order_line[0].product_id, self.test_product)
        self.assertEqual(test_order.order_line[0].product_id.name, 'Test Product')
        self.assertEqual(test_order.order_line[0].product_uom_qty, 2)
        self.assertEqual(test_order.order_line[0].price_unit, 100)
        self.assertEqual(test_order.order_line[0].price_subtotal, 200)
        self.assertEqual(test_order.amount_total, 200)

    def test_01_create_and_confirm_order(self, *args):
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
        7 - Le client doit changer de statut"""
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
        self.assertEqual(test_order.partner_id.name, 'Jean-michel client')
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

        test_order.action_confirm()
        self.assertEqual(test_order.state, 'sale')

        # Customer type change
        self.assertEqual(self.test_partner.of_customer_state, 'customer')
