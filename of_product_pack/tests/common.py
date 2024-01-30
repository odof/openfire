# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_product_brand.tests.common import TestOFProductCommon


class TestOFProdutPackCommon(TestOFProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_1, cls.product_2, cls.product_3 = cls.env['product.product'].create(
            [
                {
                    'name': "Product 1",
                    'default_code': "BA_PROD_001",
                    'brand_id': cls.product_brand_a.id,
                    'categ_id': cls.env.ref('product.product_category_all').id,
                    'standard_price': 10,
                    'list_price': 20,
                    'type': 'service',
                },
                {
                    'name': "Product 2",
                    'default_code': "BA_PROD_002",
                    'brand_id': cls.product_brand_a.id,
                    'categ_id': cls.env.ref('product.product_category_all').id,
                    'standard_price': 10,
                    'list_price': 20,
                    'type': 'service',
                },
                {
                    'name': "Product 3",
                    'default_code': "BA_PROD_003",
                    'brand_id': cls.product_brand_a.id,
                    'categ_id': cls.env.ref('product.product_category_all').id,
                    'standard_price': 10,
                    'list_price': 20,
                    'type': 'service',
                },
            ]
        )

        cls.product_pack_non_detailed = cls.env['product.product'].create(
            {
                'name': "Product pack 1 (Non Detailed)",
                'default_code': "BA_PACK_001",
                'brand_id': cls.product_brand_a.id,
                'categ_id': cls.env.ref('product.product_category_all').id,
                'pack_ok': True,
                'pack_type': 'non_detailed',
                'pack_component_price': 'totalized',
                'standard_price': 30,
                'list_price': 40,
                'type': 'service',
                'pack_line_ids': [
                    Command.create(
                        {
                            'product_id': cls.product_1.id,
                            'quantity': 1.0,
                        },
                    ),
                    Command.create(
                        {
                            'product_id': cls.product_2.id,
                            'quantity': 1.0,
                        },
                    ),
                ],
            }
        )

        cls.product_pack_detailed = cls.env['product.product'].create(
            {
                'name': "Product pack 2 (Detailed)",
                'default_code': "BA_PACK_002",
                'brand_id': cls.product_brand_a.id,
                'categ_id': cls.env.ref('product.product_category_all').id,
                'pack_ok': True,
                'pack_type': 'detailed',
                'pack_component_price': 'ignored',
                'standard_price': 30,
                'list_price': 40,
                'type': 'service',
                'pack_line_ids': [
                    Command.create(
                        {
                            'product_id': cls.product_1.id,
                            'quantity': 1.0,
                        },
                    ),
                    Command.create(
                        {
                            'product_id': cls.product_2.id,
                            'quantity': 1.0,
                        },
                    ),
                ],
            }
        )
