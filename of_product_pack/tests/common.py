# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_product_brand.tests.common import TestOFProductCommon


class TestOFProductPackCommon(TestOFProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create categories
        cls.kitchen_categ = cls.env["product.category"].create(
            {
                "name": "Kitchen",
                "parent_id": cls.env.ref("product.product_category_all").id,
            }
        )
        cls.kitchen_fork_categ = cls.env["product.category"].create(
            {
                "name": "Kitchen",
                "parent_id": cls.kitchen_categ.id,
            }
        )

        # Create products
        cls.product_spoon, cls.product_knife, cls.product_pot, cls.product_fork, cls.product_glass = cls.env[
            "product.product"
        ].create(
            [
                {
                    "name": "Spoon",
                    "default_code": "BA_SPN_001",
                    "brand_id": cls.product_brand_a.id,
                    "categ_id": cls.kitchen_categ.id,
                    "standard_price": 5,
                    "lst_price": 10.0,
                    "type": "consu",
                },
                {
                    "name": "Knife",
                    "default_code": "BA_KNF_001",
                    "brand_id": cls.product_brand_a.id,
                    "categ_id": cls.kitchen_categ.id,
                    "standard_price": 2.5,
                    "lst_price": 5.0,
                    "type": "consu",
                },
                {
                    "name": "Pot",
                    "default_code": "BA_POT_001",
                    "brand_id": cls.product_brand_a.id,
                    "categ_id": cls.kitchen_categ.id,
                    "standard_price": 15.0,
                    "lst_price": 30.0,
                    "type": "consu",
                },
                {
                    "name": "Fork",
                    "default_code": "BA_FRK_001",
                    "brand_id": cls.product_brand_a.id,
                    "categ_id": cls.kitchen_fork_categ.id,
                    "standard_price": 5.0,
                    "lst_price": 10,
                    "type": "consu",
                },
                {
                    "name": "Glass",
                    "default_code": "BA_GLS_001",
                    "brand_id": cls.product_brand_a.id,
                    "categ_id": cls.kitchen_categ.id,
                    "standard_price": 10,
                    "lst_price": 27,
                    "type": "consu",
                },
            ]
        )

        # Create packs
        cls.pack_kitchen = cls.env["product.product"].create(
            {
                "name": "Pack Kitchen 1",
                "default_code": "BA_PACK_KIT1",
                "brand_id": cls.product_brand_a.id,
                "categ_id": cls.kitchen_categ.id,
                "pack_ok": True,
                "pack_type": "non_detailed",
                "pack_component_price": "totalized",
                "standard_price": 52.5,
                "lst_price": 105.0,
                "type": "consu",
                "pack_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_spoon.id,
                            "quantity": 3.0,
                        },
                    ),
                    Command.create(
                        {
                            "product_id": cls.product_knife.id,
                            "quantity": 3.0,
                        },
                    ),
                    Command.create(
                        {
                            "product_id": cls.product_pot.id,
                            "quantity": 1.0,
                        },
                    ),
                    Command.create(
                        {
                            "product_id": cls.product_fork.id,
                            "quantity": 3.0,
                        },
                    ),
                ],
            }
        )
