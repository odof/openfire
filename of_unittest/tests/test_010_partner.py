# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import mock
from odoo.tests.common import at_install, post_install, TransactionCase


# always mock requests so as to not make call to APIs
@mock.patch('requests.request')
@mock.patch('requests.get')
@mock.patch('requests.post')
@mock.patch('requests.patch')
@mock.patch('requests.put')
@mock.patch('requests.delete')
@mock.patch('requests.head')
@mock.patch('requests.options')
@at_install(False)
@post_install(True)
class OFTestPartner(TransactionCase):

    def test_00_create_partner(self, *args):
        """ Test de création d'un partenaire.
        1 - Je prépare les valeurs par défaut du partenaire
        2 - Je crée le partenaire
        3 - Je vérifie que le partenaire a bien été créé
        4 - Je contrôle l'ordre des adresses du partenaire (facturation puis livraison)
        5 - Je contrôle le nombre d'adresses du partenaire (2 maximum)
        6 - Je contrôle que le partenaire est bien un prospect
        7 - Je simule le changement du radio bouton "client" et je contrôle que le partenaire est bien un client
        """
        partner_obj = self.env['res.partner']
        default_values = partner_obj.default_get(partner_obj.fields_get().keys())
        values = {
            'name': u'Jean-michel Apeuprès',
            'child_ids': [
                (0, 0, {
                    'name': 'Livraison', 'type': 'delivery', 'street': '1 rue de la livraison', 'zip': '75001',
                    'city': 'Paris'}),
                (0, 0, {
                    'name': 'Facturation', 'type': 'invoice', 'street': '1 rue de la facturation', 'zip': '75001',
                    'city': 'Paris'}),
            ],
        }
        default_values.update(values)
        test_partner = partner_obj.create(values)

        self.assertEqual(test_partner.name, u'Jean-michel Apeuprès')
        self.assertEqual(test_partner.of_customer_state, 'other')
        self.assertEqual(test_partner.child_ids[0].name, 'Facturation')
        self.assertEqual(test_partner.child_ids[1].name, 'Livraison')
        self.assertLessEqual(len(test_partner.child_ids), 2)

        test_partner._onchange_customer()
        self.assertEqual(test_partner.of_customer_state, 'lead')
