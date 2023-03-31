# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
from odoo.tests.common import at_install, post_install, TransactionCase


@at_install(False)
@post_install(True)
class OFTestOrderTransactionCase(TransactionCase):

    def setUp(self):
        """
        Adding basic components needed for a sale.order
        - self.test_supplier : supplier for the product
        - self.test_partner : partner that will serve as customer for the sale.order
        - self.test_category : category for the product
        - self.test_brand : brand for the product
        - self.test_product : product to use in the sale.order
        """
        super(OFTestOrderTransactionCase, self).setUp()
        self.setUpSupplier()
        self.setUpPartner()
        self.setUpProductCategory()
        self.setUpProductBrand()
        self.setUpProduct()

    def setUpSupplier(self):
        """ Supplier creation """
        partner_obj = self.env['res.partner']
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
        # affectation
        self.test_supplier = test_supplier

    def setUpPartner(self):
        """ Partner creation """
        partner_obj = self.env['res.partner']
        partner_default_values = partner_obj.default_get(partner_obj.fields_get().keys())
        # Partner creation
        values = {
            'name': 'Jean-michel client',
            'child_ids': [
                (0, 0, {
                    'name': 'Livraison', 'type': 'delivery', 'street': '1 rue de la livraison', 'zip': '35000',
                    'city': 'Rennes'}),
                (0, 0, {
                    'name': 'Facturation', 'type': 'invoice', 'street': '2 rue de la facturation', 'zip': '35000',
                    'city': 'Rennes'}),
            ],
            'user_id': self.env.user.id,
        }
        partner_default_values.update(values)
        test_partner = partner_obj.create(values)
        self.assertEqual(test_partner.name, 'Jean-michel client')
        self.assertEqual(test_partner.of_customer_state, 'other')
        self.assertEqual(test_partner.child_ids[0].name, 'Facturation')
        self.assertEqual(test_partner.child_ids[1].name, 'Livraison')
        self.assertLessEqual(len(test_partner.child_ids), 2)
        test_partner._onchange_customer()
        self.assertEqual(test_partner.of_customer_state, 'lead')
        # affectation
        self.test_partner = test_partner

    def setUpProductCategory(self):
        """ Product category creation """
        product_category_obj = self.env['product.category']
        # Category creation
        default_values = product_category_obj.default_get(product_category_obj.fields_get().keys())
        values = {
            'name': u'Catégorie test',
        }
        default_values.update(values)
        test_category = product_category_obj.create(values)
        self.assertNotEqual(test_category, product_category_obj)
        # affectation
        self.test_category = test_category

    def setUpProductBrand(self):
        """ Brand creation """
        if not hasattr(self, 'test_supplier') or not hasattr(self, 'test_category'):
            return
        product_brand_obj = self.env['of.product.brand']
        default_values = product_brand_obj.default_get(product_brand_obj.fields_get().keys())
        values = {
            'name': 'Brand Test',
            'code': 'BT',
            'partner_id': self.test_supplier.id,
            'of_import_categ_id': self.test_category.id,
            'of_import_remise': 40,
            'of_import_price': 'ppht',
            'of_import_cout': 'pa',
        }
        default_values.update(values)
        test_brand = product_brand_obj.create(values)
        self.assertNotEqual(test_brand, product_brand_obj)
        # affectation
        self.test_brand = test_brand

    def setUpProduct(self):
        """ Product creation """
        if not hasattr(self, 'test_brand'):
            return
        product_obj = self.env['product.product']
        default_values = product_obj.default_get(product_obj.fields_get().keys())
        values = {
            'name': 'Test Product',
            'type': 'product',
            'standard_price': 80,
            'list_price': 100,
            'of_seller_price': 80,
            'of_seller_pp_ht': 100,
            'brand_id': self.test_brand.id,
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
        # affectation
        self.test_product = test_product


@at_install(False)
@post_install(True)
class OFAdvancedTestOrderTransactionCase(OFTestOrderTransactionCase):

    def setUp(self):
        """
        Making a basic sale.order to test functionnalities beyond it's creation
        - self.test_order : sale.order for the tests
        """
        super(OFAdvancedTestOrderTransactionCase, self).setUp()
        self.setUpOrder()

    def setUpOrder(self):
        if not hasattr(self, 'test_partner') or not hasattr(self, 'test_product'):
            return
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
        self.test_order = test_order

