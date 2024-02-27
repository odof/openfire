from odoo.tests.common import TransactionCase


class TestOFProductProduct(TransactionCase):
    def setUp(self):
        super().setUp()
        self.ProductProduct = self.env['product.product']
        self.long_name = (
            'Test Product with a long name that is greater than 120 characters and that should be '
            'shorten to 120 characters if the context is set to show_shorten_name.'
        )
        self.long_name_shorten = (
            'Test Product with a long name that is greater than 120 characters and that should '
            'be shorten to 120 characters if the co...'
        )
        self.product = self.ProductProduct.create({'name': self.long_name})

    def test_01_product_show_shorten_name(self):
        name = self.product.name_get()
        self.assertEqual(name, [(self.product.id, self.long_name)])

        name = self.product.with_context(show_shorten_name=10).name_get()
        self.assertEqual(name, [(self.product.id, 'Test Produ...')])

        name = self.product.with_context(show_shorten_name=True).name_get()
        self.assertEqual(name, [(self.product.id, self.long_name_shorten)])
