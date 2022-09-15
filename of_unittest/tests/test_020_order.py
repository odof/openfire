# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.of_unittest.tests.test_order_common import OFTestOrderTransactionCase


class OFTestOrder(OFTestOrderTransactionCase):

    def test_00_create_order(self):
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
        self.assertEqual(test_order.partner_id.name, 'Jean-michel Voixdechiotte')
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
