# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
import datetime
from odoo.addons.of_unittest.tests.test_order_common import OFAdvancedTestOrderTransactionCase

 # always mock requests so as to not make call to APIs
@mock.patch('requests.request')
@mock.patch('requests.get')
@mock.patch('requests.post')
@mock.patch('requests.patch')
@mock.patch('requests.put')
@mock.patch('requests.delete')
@mock.patch('requests.head')
@mock.patch('requests.options')
class OFTestOrder(OFAdvancedTestOrderTransactionCase):

    def test_02_create_and_confirm_order(self, *args):
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
        8 - Un bon de livraison doit avoir été généré
        9 - Je demande d'approvisionner mes articles et je vérifie qu'une CF existe
        10 - Je valide la CF et BR associé
        11 - Je valide le BL
        """
        test_order = self.test_order
        # on confirme la commande et on vérifie qu'on est passé a l'état sale
        test_order.action_confirm()
        self.assertEqual(test_order.state, 'sale')
        # on vérifie que le bon de livraison existe
        self.assertEqual(len(test_order.picking_ids), 1)
        # On appro et vérifie que la CF est créée
        test_order.picking_ids.button_procure_all()
        self.assertGreater(len(test_order.picking_ids.of_purchase_ids), 0)
        for purchase_order in test_order.picking_ids.of_purchase_ids:
            # confirmation de la commande
            purchase_order.button_confirm()
            # vérification que le BR existe avec des opérations
            self.assertEqual(len(purchase_order.picking_ids), 1)
            self.assertGreater(len(purchase_order.picking_ids.pack_operation_product_ids), 0)
            for pack_operation in purchase_order.picking_ids.pack_operation_product_ids:
                pack_operation.qty_done = pack_operation.product_qty
            # valider le BR
            purchase_order.picking_ids.do_new_transfer()
            # le BR est a l'état 'fait'
            self.assertEqual(purchase_order.picking_ids.state, 'done')
        # vérifier que le BL a maintenant des opérations
        self.assertGreater(len(test_order.picking_ids.pack_operation_product_ids), 0)
        for pack_operation in test_order.picking_ids.pack_operation_product_ids:
            pack_operation.qty_done = pack_operation.product_qty
        # valider le BL
        test_order.picking_ids.do_new_transfer()
        # le BL est a l'état 'fait'
        self.assertEqual(test_order.picking_ids.state, 'done')



