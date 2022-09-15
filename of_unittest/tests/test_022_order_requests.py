# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
from odoo.addons.of_unittest.tests.test_order_common import OFTestOrderTransactionCase


class OFTestOrder(OFTestOrderTransactionCase):

    @mock.patch('odoo.addons.of_unittest.models.sale_status_code.requests.get')
    def test_04_create_and_confirm_order_requests(self, requests_get_mock):
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
        8 - Je souhaite tester l'envoi la récupération du status de la requete
            - Si status_code == 200 alors le champ est mis à jour, sinon rien"""
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
            test_order.action_confirm()
            m.assert_called_once()

        self.assertEqual(test_order.state, 'sale')

        # Test status code of the Sale order
        # Mock the get response OK
        requests_get_mock.return_value = mock.Mock(status_code=200, json=lambda: {'code': 'CODE123'})
        test_order._synchronize_status_code()
        self.assertEqual(test_order.status_code, 'CODE123')

        # Mock the get response NOK
        requests_get_mock.return_value = mock.Mock(status_code=404, json=lambda: {'code': 'CODE456'})
        test_order._synchronize_status_code()
        self.assertEqual(test_order.status_code, False)
