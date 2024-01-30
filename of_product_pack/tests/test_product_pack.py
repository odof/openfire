# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form
from odoo.tools import mute_logger

from odoo.addons.of_product_pack.tests.common import TestOFProdutPackCommon


class TestProductPack(TestOFProdutPackCommon):
    def test_01_product_pack_recursion(self):
        """Test that adding a pack in itself raises an error."""
        with self.assertRaises(ValidationError):
            self.product_pack_non_detailed.write(
                {
                    'pack_line_ids': [
                        Command.create(
                            {
                                'product_id': self.product_pack_non_detailed.id,
                                'quantity': 1.0,
                            },
                        )
                    ]
                }
            )

    @mute_logger('odoo.sql_db')
    def test_02_product_in_pack_unique(self):
        """Test that adding a product that is already in the concerned pack raises an error."""
        with self.assertRaises(IntegrityError):
            self.product_pack_non_detailed.write(
                {
                    'pack_line_ids': [
                        Command.create(
                            {
                                'product_id': self.product_1.id,
                                'quantity': 1.0,
                            },
                        )
                    ]
                }
            )

    def test_03_get_pack_line_price(self):
        """Test list price computation for pack components."""
        component = self.product_pack_non_detailed.pack_line_ids[0]
        component.product_id.list_price = 30.0
        self.assertEqual(
            30.0,
            self.product_pack_non_detailed.pack_line_ids.filtered(
                lambda line: line.product_id == component.product_id
            ).get_price(),
        )

    def test_04_get_pack_lst_price(self):
        """Test list price computation for detailed and non-detailed packs."""
        component_1 = self.product_pack_detailed.pack_line_ids[0]
        component_1.product_id.list_price = 30.0
        component_2 = self.product_pack_detailed.pack_line_ids[1]
        component_2.product_id.list_price = 15.0
        self.assertEqual(40.0, self.product_pack_detailed.lst_price)  # `pack_component_price` is set to 'ignored'

        component_1 = self.product_pack_non_detailed.pack_line_ids[0]  # `pack_component_price` is set to 'totalized'
        component_1.product_id.list_price = 15.0
        component_2 = self.product_pack_non_detailed.pack_line_ids[1]
        component_2.product_id.list_price = 15.0
        self.assertEqual(30.0, self.product_pack_non_detailed.lst_price)

    def test_05_pack_type(self):
        """Test case to verify the behavior of pack_modifiable property.
        when changing the pack type."""
        pack = self.product_pack_detailed.product_tmpl_id
        pack.pack_modifiable = True
        with Form(pack) as pack_form:
            pack_form.pack_type = 'non_detailed'
        self.assertFalse(pack_form.pack_modifiable)

    def test_06_pack_modifiable(self):
        """Test case to verify the behavior of pack_modifiable_invisible property.
        when changing the pack type and pack component price."""
        pack = self.product_pack_detailed.product_tmpl_id
        pack.pack_type = 'detailed'
        self.assertFalse(pack.pack_modifiable_invisible)
        pack.pack_type = 'non_detailed'
        self.assertTrue(pack.pack_modifiable_invisible)
        pack.pack_type = 'detailed'
        pack.pack_component_price = 'totalized'
        self.assertFalse(pack.pack_modifiable_invisible)

    def test_07_price_compute_with_pricelist_context(self):
        product_pack = self.product_pack_detailed
        component_1 = product_pack.pack_line_ids[0]
        component_1.product_id.list_price = 30.0
        component_2 = product_pack.pack_line_ids[1]
        component_2.product_id.list_price = 15.0
        price = product_pack.with_context(pricelist='pricelist test').price_compute('list_price').get(product_pack.id)
        self.assertEqual(price, 40.0)
