# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import mock
from odoo.addons.of_unittest.tests.test_order_common import OFTestOrderTransactionCase
from odoo.addons.of_unittest.tests.test_users_common import OFTestUsersTransactionCase

from odoo.exceptions import UserError, AccessError, MissingError, ValidationError


 # always mock requests so as to not make call to APIs
@mock.patch('requests.request')
@mock.patch('requests.get')
@mock.patch('requests.post')
@mock.patch('requests.patch')
@mock.patch('requests.put')
@mock.patch('requests.delete')
@mock.patch('requests.head')
@mock.patch('requests.options')
class OFTestOrder(OFTestOrderTransactionCase, OFTestUsersTransactionCase):

    def setUp(self):
        super(OFTestOrder, self).setUp()
        self.setUpGestionnaire()
        self.setUpPortail()
        self.setUpVendeur()
        self.setUpAssistant()

    def test_00_create_order_Gestionnaire(self, *args):
        """ Tests des droits de différents utilisateurs type """
        # -- Tests des droits utilisateur gestionnaire
        sale_order_obj_gestionnaire = self.model_obj_as_user('sale.order', self.gestionnaire.id)
        sale_order_line_obj_gestionnaire = self.model_obj_as_user('sale.order.line', self.gestionnaire.id)
        order_values = sale_order_obj_gestionnaire.default_get(sale_order_obj_gestionnaire.fields_get().keys())
        order_values.update({
            'partner_id': self.test_partner.id,
        })
        # Sale order creation
        test_order = sale_order_obj_gestionnaire.create(order_values)
        test_order.onchange_partner_id()
        self.assertNotEqual(test_order, sale_order_obj_gestionnaire)
        self.assertEqual(test_order.partner_id.name, 'Jean-michel client')
        self.assertEqual(test_order.partner_shipping_id.name, 'Livraison')
        self.assertEqual(test_order.partner_invoice_id.name, 'Facturation')
        # Order line creation
        line_values = sale_order_line_obj_gestionnaire.default_get(sale_order_line_obj_gestionnaire.fields_get().keys())
        line_values.update({
            'product_id': self.test_product.id,
            'product_uom_qty': 2,
            'order_id': test_order.id
        })
        test_order_line = sale_order_line_obj_gestionnaire.create(line_values)
        test_order_line.product_id_change()
        self.assertEqual(test_order.order_line[0].product_id, self.test_product)
        self.assertEqual(test_order.order_line[0].product_id.name, 'Test Product')
        self.assertEqual(test_order.order_line[0].product_uom_qty, 2)
        self.assertEqual(test_order.order_line[0].price_unit, 100)
        self.assertEqual(test_order.order_line[0].price_subtotal, 200)
        self.assertEqual(test_order.amount_total, 200)

        # -- Tests des droits utilisateur portail
        sale_order_obj_portail = self.model_obj_as_user('sale.order', self.portail.id)
        # A portal user can't create sale.order, should raise an error when trying to get next name from sequence
        with self.assertRaises(AccessError) as ae:
            order_values = sale_order_obj_portail.default_get(sale_order_obj_portail.fields_get().keys())
            order_values.update({
                'partner_id': self.test_partner.id,
            })
            test_order = sale_order_obj_portail.create(order_values)

        # -- Tests des droits utilisateur vendeur
        sale_order_obj_vendeur = self.model_obj_as_user('sale.order', self.vendeur.id)
        order_values = sale_order_obj_vendeur.default_get(sale_order_obj_vendeur.fields_get().keys())
        order_values.update({
            'partner_id': self.test_partner.id,
        })
        test_order = sale_order_obj_vendeur.create(order_values)
        with self.assertRaises(AccessError) as cm:
            test_order.onchange_partner_id()

         # -- Tests des droits utilisateur assistant
        sale_order_obj_assistant = self.model_obj_as_user('sale.order', self.assistant.id)
        order_values = sale_order_obj_assistant.default_get(sale_order_obj_assistant.fields_get().keys())
        order_values.update({
            'partner_id': self.test_partner.id,
        })
        test_order = sale_order_obj_assistant.create(order_values)
        test_order.onchange_partner_id()
        self.assertNotEqual(test_order, sale_order_obj_assistant)
        self.assertEqual(test_order.partner_id.name, 'Jean-michel client')
        self.assertEqual(test_order.partner_shipping_id.name, 'Livraison')
        self.assertEqual(test_order.partner_invoice_id.name, 'Facturation')

