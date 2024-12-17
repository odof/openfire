# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

from odoo.addons.of_product_pack.tests.common import TestOFProductPackCommon


class TestProductPack(TestOFProductPackCommon):
    def test_01_product_pack_recursion(self):
        """Test that adding a pack in itself raises an error."""
        with self.assertRaises(ValidationError):
            self.pack_kitchen.write(
                {
                    "pack_line_ids": [
                        Command.create(
                            {
                                "product_id": self.pack_kitchen.id,
                                "quantity": 1.0,
                            },
                        )
                    ]
                }
            )

    @mute_logger("odoo.sql_db")
    def test_02_product_in_pack_unique(self):
        """Test that adding a product that is already in the concerned pack raises an error."""
        with self.assertRaises(IntegrityError):
            self.pack_kitchen.write(
                {
                    "pack_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_spoon.id,
                                "quantity": 1.0,
                            },
                        )
                    ]
                }
            )

    def test_03_get_pack_line_price(self):
        """Test list price computation for pack components."""
        component = self.pack_kitchen.pack_line_ids[0]

        # Change price from 10.0 to 30.0
        component.product_id.list_price = 30.0
        self.assertEqual(
            90.0,  # 3 * 30.0
            self.pack_kitchen.pack_line_ids.filtered(lambda line: line.product_id == component.product_id).get_price(),
        )

    def test_04_get_pack_lst_price(self):
        """Test list price computation for totalized/ignored price packs."""
        self.pack_kitchen.pack_component_price = "ignored"

        component_spoon = self.pack_kitchen.pack_line_ids[0]
        component_spoon.product_id.list_price = 30.0  # was 10.0
        component_knife = self.pack_kitchen.pack_line_ids[1]
        component_knife.product_id.list_price = 15.0  # was 5.0
        # price won't be computed as pack_component_price is ignored, still 105.0
        self.assertEqual(105.0, self.pack_kitchen.lst_price)

        # Set back original prices
        component_spoon.product_id.list_price = 10.0
        component_knife.product_id.list_price = 5.0

        # Change price computation to totalized
        self.pack_kitchen.pack_component_price = "totalized"

        # Change price of components
        component_spoon = self.pack_kitchen.pack_line_ids[0]
        component_spoon.product_id.list_price = 15.0  # was 10.0
        component_knife = self.pack_kitchen.pack_line_ids[1]
        component_knife.product_id.list_price = 15.0  # was 5.0
        self.assertEqual(150.0, self.pack_kitchen.lst_price)

    def test_05_pack_modifiable(self):
        """Test case to verify the behavior of pack_modifiable_invisible property when changing the pack type and
        pack component price."""
        pack = self.pack_kitchen.product_tmpl_id
        pack.pack_type = "detailed"
        self.assertFalse(pack.pack_modifiable_invisible)
        pack.pack_type = "non_detailed"
        self.assertTrue(pack.pack_modifiable_invisible)
        pack.pack_type = "detailed"
        pack.pack_component_price = "totalized"
        self.assertFalse(pack.pack_modifiable_invisible)
