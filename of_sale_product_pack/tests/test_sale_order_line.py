# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import Form

from odoo.addons.of_product_pack.tests.common import TestOFProdutPackCommon
from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestSaleOrderLine(TestOFProdutPackCommon, TestOFSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        return super().setUp()

    def test_00_sale_order_line_of_pack_ok(self):
        """Test if pack_ok product are correctly passed to the sale order line"""
        self.assertEqual(self.product_1.pack_ok, False)

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_1.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order_pack_not_ok = self.env["sale.order"].create(order_values)
        self.assertEqual(order_pack_not_ok.order_line[0].of_pack_ok, False)

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_pack_detailed.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order_pack_ok = self.env["sale.order"].create(order_values)
        self.assertEqual(order_pack_ok.order_line[0].of_pack_ok, True)

    def test_01_sale_order_line_of_pack_type(self):
        """Test if sale order line are correctly created and removed when changing of_pack_type"""
        self.assertEqual(self.product_pack_detailed.pack_type, "detailed")

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_pack_detailed.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)
        # 3 because the pack has 2 components
        self.assertEqual(len(order.order_line), 3)

        pack_order_line = order.order_line.filtered(
            lambda line: line.product_id == self.product_pack_detailed and line.of_pack_ok
        )

        # Change the pack type to 'non_detailed' and check if the pack components are removed
        pack_order_line.of_pack_type = "non_detailed"
        self.assertEqual(len(order.order_line), 1)

        # Change the pack type to 'detailed' and check if the pack components are added back
        pack_order_line.of_pack_type = "detailed"
        self.assertEqual(len(order.order_line), 3)

    def test_02_sale_order_line_of_pack_component_price(self):
        """Test if price_unit is correctly computed when pack_component_price is 'totalized' or 'ignored'"""

        self.assertEqual(self.product_pack_detailed.pack_component_price, "ignored")

        # Set the list price of the pack components differently to check the price_unit computation
        self.product_pack_detailed.pack_line_ids[0].product_id.list_price = 20.0
        self.product_pack_detailed.pack_line_ids[1].product_id.list_price = 10.0

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_pack_detailed.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)
        self.assertEqual(len(order.order_line), 3)

        pack_order_line = order.order_line.filtered(
            lambda line: line.product_id == self.product_pack_detailed and line.of_pack_ok
        )
        # Should be 40.0 because pack_component_price is 'ignored' and we set the list price of the pack components
        # to 40.0
        self.assertEqual(pack_order_line.price_unit, 40.0)

        # Change the pack_component_price to 'totalized'
        pack_order_line.of_pack_component_price = "totalized"

        # Should be sum of the list prices of the pack components
        self.assertEqual(pack_order_line.price_unit, 30.0)

    def test_03_sale_order_line_of_pack_line_ids(self):
        """
        Test case to verify the behavior of pack line ids in sale order line.

        Steps:
        1. Create a Sale Order with a pack product (2 components) and verify that Order has 3 order lines.
        2. Add a new product to the pack order line and verify that the sale order line is created.
        3. Change the pack type to 'non_detailed' and verify that all the pack components are removed.
        4. Set the pack type back to 'detailed' and verify that the pack components are added back with the manually
            added product.
        5. Remove one item from the pack order line and verify that the sale order line is removed.
        6. Add a new line with the same product as one of the pack components and verify that when the pack component is
            removed, the stand-alone line is not removed.

        Assertions:
        - The sale order should have the expected number of order lines at each step.
        - The pack order line should have the expected number of pack line ids at each step.
        - The removed pack component should not be present in the sale order line.
        - The removed pack component should be present when added back to the pack order line.
        - The stand-alone line with the same product as a pack component should not be removed when the pack
            component is removed.
        """
        self.assertEqual(self.product_pack_detailed.pack_type, "detailed")

        new_product = self.env["product.product"].create(
            {
                "name": "Product 4",
                "default_code": "BA_PROD_004",
                "brand_id": self.product_brand_a.id,
                "categ_id": self.env.ref("product.product_category_all").id,
                "standard_price": 10,
                "list_price": 20,
                "type": "service",
            },
        )

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_pack_detailed.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)
        self.assertEqual(len(order.order_line), 3)

        pack_order_line = order.order_line.filtered(
            lambda line: line.product_id == self.product_pack_detailed and line.of_pack_ok
        )

        self.assertEqual(len(pack_order_line.of_pack_line_ids), 2)
        self.assertEqual(
            pack_order_line.of_pack_line_ids.mapped("product_id"),
            self.product_pack_detailed.pack_line_ids.mapped("product_id"),
        )

        # Add a new product into the pack in sale order line
        # Check that a new sale order line is created for the new product
        pack_order_line.of_pack_line_ids = [
            Command.create(
                {
                    "product_id": new_product.id,
                    "quantity": 1.0,
                },
            ),
        ]
        self.assertEqual(len(pack_order_line.of_pack_line_ids), 3)
        self.assertEqual(
            pack_order_line.of_pack_line_ids.mapped("product_id"),
            self.product_pack_detailed.pack_line_ids.mapped("product_id") | new_product,
        )
        self.assertEqual(len(order.order_line), 4)  # 4 because the pack has 3 components (2 original + 1 new)

        # Change the pack type to 'non_detailed' and check if the pack components are removed
        pack_order_line.of_pack_type = "non_detailed"
        self.assertEqual(len(order.order_line), 1)

        # Set it back to 'detailed' and check if the pack components are added back
        pack_order_line.of_pack_type = "detailed"
        self.assertEqual(len(order.order_line), 4)  # 4 because the pack has 2 components (2 original + 1 new)
        print(order.order_line.mapped(lambda line: (line.product_id, line.product_id.name)))

        # Remove on item from the pack in sale order line
        removed_line = pack_order_line.of_pack_line_ids.filtered(lambda line: line.product_id == self.product_2)
        pack_order_line.of_pack_line_ids -= removed_line

        # Check that the sale order line is removed
        self.assertEqual(len(pack_order_line.of_pack_line_ids), 2)
        self.assertEqual(len(order.order_line), 3)
        self.assertFalse(
            order.order_line.filtered(
                lambda line: line.product_id == self.product_2 and line.pack_parent_line_id == pack_order_line
            )
        )

        # Add the removed item back to the pack in sale order line
        pack_order_line.of_pack_line_ids = [
            Command.create(
                {
                    "product_id": self.product_2.id,
                    "quantity": 1.0,
                },
            ),
        ]
        self.assertTrue(
            order.order_line.filtered(
                lambda line: line.product_id == self.product_2 and line.pack_parent_line_id == pack_order_line
            )
        )

        # Add new line stand alone line that contains the same product as one of the pack components
        # Then remove the pack component and check that the stand alone line is not removed
        order.order_line = [
            Command.create(
                {
                    "product_id": new_product.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        self.assertEqual(len(order.order_line), 5)
        removed_line = pack_order_line.of_pack_line_ids.filtered(lambda line: line.product_id == new_product)
        pack_order_line.of_pack_line_ids -= removed_line

        self.assertEqual(len(pack_order_line.of_pack_line_ids), 2)
        self.assertEqual(len(order.order_line), 4)
        self.assertTrue(
            order.order_line.filtered(lambda line: line.product_id == new_product and not line.pack_parent_line_id)
        )

    def test_04_sale_order_line_product_uom_qty_ignored(self):
        """Test if the quantities (and the price unit) are correctly computed on the sale order lines
        for an ignored component price on pack"""
        order_values = self._prepare_empty_sale_order_values()

        # On rajoute un pack
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_pack_detailed.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)
        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[1].product_uom_qty, 1)
        self.assertEqual(order.order_line[2].product_uom_qty, 1)
        self.assertEqual(order.order_line[0].price_unit, 40)
        self.assertEqual(order.order_line[1].price_unit, 0)
        self.assertEqual(order.order_line[2].price_unit, 0)

        # On modifie les quantités des composants du pack
        with Form(order.order_line[0], "of_sale_product_pack.of_sale_order_line_view") as line_form:
            with line_form.of_pack_line_ids.edit(0) as pack_line_form:
                pack_line_form.quantity = 2
                pack_line_form.save()
            with line_form.of_pack_line_ids.edit(1) as pack_line_form:
                pack_line_form.quantity = 3
                pack_line_form.save()
            line_form.save()

        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[1].product_uom_qty, 2)
        self.assertEqual(order.order_line[2].product_uom_qty, 3)
        self.assertEqual(order.order_line[0].price_unit, 40)
        self.assertEqual(order.order_line[1].price_unit, 0)
        self.assertEqual(order.order_line[2].price_unit, 0)

        # On modifie le nombre de pack
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 2
                line_form.save()
            order = order_form.save()

        self.assertEqual(order.order_line[0].product_uom_qty, 2)
        self.assertEqual(order.order_line[1].product_uom_qty, 4)
        self.assertEqual(order.order_line[2].product_uom_qty, 6)
        self.assertEqual(order.order_line[0].price_unit, 40)
        self.assertEqual(order.order_line[1].price_unit, 0)
        self.assertEqual(order.order_line[2].price_unit, 0)

    def test_05_sale_order_line_product_uom_qty_totalized(self):
        """Test if the quantities (and the price unit) are correctly computed on the sale order lines
        for an ignored component price on pack"""
        order_values = self._prepare_empty_sale_order_values()

        # On rajoute un pack
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_pack_non_detailed.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)
        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[0].price_unit, 32.0)

        # On modifie les quantités des composants du pack
        with Form(order.order_line[0], "of_sale_product_pack.of_sale_order_line_view") as line_form:
            with line_form.of_pack_line_ids.edit(0) as pack_line_form:
                pack_line_form.quantity = 2
                pack_line_form.save()
            with line_form.of_pack_line_ids.edit(1) as pack_line_form:
                pack_line_form.quantity = 3
                pack_line_form.save()
            line_form.save()

        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[0].price_unit, 84.0)

        # On modifie le nombre de pack
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 2
                line_form.save()
            order = order_form.save()

        self.assertEqual(order.order_line[0].product_uom_qty, 2)
        self.assertEqual(order.order_line[0].price_unit, 84.0)
