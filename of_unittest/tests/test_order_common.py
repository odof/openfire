# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import at_install, post_install, TransactionCase


@at_install(False)
@post_install(True)
class OFTestOrderTransactionCase(TransactionCase):

    def setUp(self):
        super(OFTestOrderTransactionCase, self).setUp()

        partner_obj = self.env['res.partner']
        product_obj = self.env['product.product']
        product_brand_obj = self.env['of.product.brand']
        product_category_obj = self.env['product.category']

        partner_default_values = partner_obj.default_get(partner_obj.fields_get().keys())
        # Supplier creation
        values = {
            'name': 'Jean-michel Fournisseur',
            'supplier': True,
            'is_company': True,
        }
        partner_default_values.update(values)
        test_supplier = partner_obj.create(values)
        self.assertEqual(test_supplier.name, 'Jean-michel Fournisseur')
        self.assertEqual(test_supplier.is_company, True)
        self.assertEqual(test_supplier.supplier, True)

        # Partner creation
        values = {
            'name': 'Jean-michel Voixdechiotte',
            'child_ids': [
                (0, 0, {
                    'name': 'Livraison', 'type': 'delivery', 'street': '1 rue de la livraison', 'zip': '35000',
                    'city': 'Rennes'}),
                (0, 0, {
                    'name': 'Facturation', 'type': 'invoice', 'street': '2 rue de la facturation', 'zip': '35000',
                    'city': 'Rennes'}),
            ],
        }
        partner_default_values.update(values)
        test_partner = partner_obj.create(values)
        self.assertEqual(test_partner.name, 'Jean-michel Voixdechiotte')
        self.assertEqual(test_partner.of_customer_state, 'other')
        self.assertEqual(test_partner.child_ids[0].name, 'Facturation')
        self.assertEqual(test_partner.child_ids[1].name, 'Livraison')
        self.assertLessEqual(len(test_partner.child_ids), 2)
        test_partner._onchange_customer()
        self.assertEqual(test_partner.of_customer_state, 'lead')

        # Category creation
        default_values = product_category_obj.default_get(product_category_obj.fields_get().keys())
        values = {
            'name': u'Catégorie test',
        }
        default_values.update(values)
        test_category = product_category_obj.create(values)
        self.assertNotEqual(test_category, product_category_obj)

        # Brand creation
        default_values = product_brand_obj.default_get(product_brand_obj.fields_get().keys())
        values = {
            'name': 'Brand Test',
            'code': 'BT',
            'partner_id': test_supplier.id,
            'of_import_categ_id': test_category.id,
            'of_import_remise': 40,
            'of_import_price': 'ppht',
            'of_import_cout': 'pa',
        }
        default_values.update(values)
        test_brand = product_brand_obj.create(values)
        self.assertNotEqual(test_brand, product_brand_obj)

        # Product creation
        default_values = product_obj.default_get(product_obj.fields_get().keys())
        values = {
            'name': 'Test Product',
            'type': 'product',
            'standard_price': 80,
            'list_price': 100,
            'of_seller_price': 80,
            'of_seller_pp_ht': 100,
            'brand_id': test_brand.id,
        }
        default_values.update(values)
        test_product = product_obj.create(values)
        self.assertNotEqual(test_product, product_obj)
        test_product._onchange_brand_id()
        test_product.default_code = 'BT_TEST'

        self.assertEqual(test_product.list_price, 100)
        self.assertEqual(test_product.marge, 20.0)
        self.assertEqual(len(test_product.seller_ids), 1)
        test_product.seller_ids[0].price = 80
        test_product.seller_ids[0].pp_ht = 100
        self.assertEqual(test_product.of_seller_remise, 20.0)

        self.test_supplier = test_supplier
        self.test_partner = test_partner
        self.test_category = test_category
        self.test_brand = test_brand
        self.test_product = test_product