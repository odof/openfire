# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form

from odoo.addons.of_product_pack.tests.common import TestOFProductPackCommon
from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleOrderLinePack(TestOFProductPackCommon, TestOFSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist_kitchen = (
            cls.env["product.pricelist"]
            .with_company(cls.company_fr)
            .create(
                {
                    "name": "Kitchen Pricelist (EUR)",
                    "currency_id": cls.company_fr.currency_id.id,
                    "item_ids": [
                        Command.create(
                            {
                                "compute_price": "fixed",
                                "applied_on": "1_product",
                                "fixed_price": 15.0,
                                "product_tmpl_id": cls.product_glass.id,
                            }
                        ),
                        Command.create(
                            {
                                "compute_price": "percentage",
                                "applied_on": "1_product",
                                "percent_price": 10.0,
                                "product_tmpl_id": cls.product_pot.id,
                            }
                        ),
                        Command.create(
                            {
                                "compute_price": "percentage",
                                "applied_on": "1_product",
                                "percent_price": 5.0,
                                "product_tmpl_id": cls.product_spoon.id,
                            }
                        ),
                        Command.create(
                            {
                                "compute_price": "fixed",
                                "applied_on": "2_product_category",
                                "fixed_price": 5.0,
                                "categ_id": cls.kitchen_fork_categ.id,
                            }
                        ),
                    ],
                }
            )
        )

        cls.pricelist_kitchen_25perc = (
            cls.env["product.pricelist"]
            .with_company(cls.company_fr)
            .create(
                {
                    "name": "Pot 25% (EUR)",
                    "currency_id": cls.company_fr.currency_id.id,
                    "item_ids": [
                        Command.create(
                            {
                                "compute_price": "percentage",
                                "percent_price": 25.0,
                                "applied_on": "1_product",
                                "product_tmpl_id": cls.product_pot.id,
                                "min_quantity": 1.0,
                            },
                        ),
                    ],
                }
            )
        )

    def setUp(self):
        return super().setUp()

    def test_01_sale_order_line_of_pack_ok(self):
        """Test if `pack_ok` is correctly computed on the sale order line"""
        self.assertEqual(self.product_spoon.pack_ok, False)

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.product_spoon.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order1 = self.env["sale.order"].create(order_values)
        self.assertEqual(order1.order_line[0].of_pack_ok, False)

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.pack_kitchen.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order2 = self.env["sale.order"].create(order_values)
        self.assertEqual(order2.order_line[0].of_pack_ok, True)

    def test_02_sale_order_line_of_pack_component_price(self):
        """Test if `price_unit` is correctly computed when pack_component_price is 'totalized' or 'ignored'"""
        self.pack_kitchen.pack_component_price = "ignored"

        self.assertEqual(self.pack_kitchen.pack_component_price, "ignored")

        # Change the list prices of the pack components manually as the pack_component_price is 'ignored'
        self.pack_kitchen.list_price = 200.0

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.pack_kitchen.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)
        self.assertEqual(len(order.order_line), 1)
        pack_order_line = order.order_line.filtered(
            lambda line: line.product_id == self.pack_kitchen and line.of_pack_ok
        )

        # Should be `200.0` because pack_component_price is 'ignored' and we set the list price of the pack components
        # manually
        self.assertEqual(pack_order_line.price_unit, 200.0)

        # Change back the pack_component_price to 'totalized' and change the list prices of the pack components
        pack_order_line.of_pack_component_price = "totalized"
        pack_order_line.of_pack_line_ids[0].price_unit = 10.0  # (Spoon, was 10.0)
        pack_order_line.of_pack_line_ids[1].price_unit = 20.0  # (Knife, was 5.0)

        # Should be sum of the list prices of the pack components (10.0 * 3 + 20.0 * 3 + 30.0 * 1 + 10.0 * 3 = 150.0)
        self.assertEqual(pack_order_line.price_unit, 150.0)

    def test_03_sale_order_line_of_pack_line_ids(self):
        """Test the behavior of sale order lines when dealing with product packs.

        This test covers the following scenarios:
        1. Creating a sale order with a detailed pack and verifying the pack components in the sale order lines.
        2. Adding a new product to the pack and verifying the updated pack components in the sale order lines.
        3. Changing the pack type to 'non_detailed' and verifying the removal of pack components from the
            sale order lines.
        4. Reverting the pack type to 'detailed' and verifying the re-addition of pack components in the
            sale order lines.
        5. Removing a component from the pack and verifying the updated pack components in the sale order lines.
        6. Adding the removed component back to the pack and verifying the updated pack components in the
            sale order lines.
        7. Adding a stand-alone line with a product that is also a pack component and verifying the sale order lines.
        8. Removing a pack component that is also a stand-alone line and verifying the sale order lines are not removed.
        """
        self.pack_kitchen.pack_type = "detailed"
        self.assertEqual(self.pack_kitchen.pack_type, "detailed")

        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.pack_kitchen.id,  # Pack Kitchen (detailed)
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)
        self.assertEqual(len(order.order_line), 5)  # 1 Pack line and its 4 components

        # Find the pack order line
        pack_order_line = order.order_line.filtered(
            lambda line: line.product_id == self.pack_kitchen and line.of_pack_ok
        )

        # Check that the pack order line has 4 pack line ids composed of the pack components
        self.assertEqual(len(pack_order_line.of_pack_line_ids), 4)
        self.assertEqual(
            pack_order_line.of_pack_line_ids.mapped("product_id"),
            self.pack_kitchen.pack_line_ids.mapped("product_id"),
        )

        # Add a new product into the pack in sale order line and check that a new sale order line is created for this
        # new product
        new_product = self.env["product.product"].create(
            {
                "name": "New Product",
                "default_code": "BA_PROD_NEW",
                "brand_id": self.product_brand_a.id,
                "categ_id": self.env.ref("product.product_category_all").id,
                "standard_price": 10,
                "lst_price": 20,
                "type": "service",
            },
        )
        pack_order_line.of_pack_line_ids = [
            Command.create(
                {
                    "product_id": new_product.id,
                    "quantity": 1.0,
                },
            ),
        ]
        self.assertEqual(len(pack_order_line.of_pack_line_ids), 5)
        self.assertEqual(
            pack_order_line.of_pack_line_ids.mapped("product_id"),
            self.pack_kitchen.pack_line_ids.mapped("product_id") | new_product,
        )
        self.assertEqual(len(order.order_line), 6)  # 1 Pack line and its 5 components (including the new product)

        # Change the pack type to 'non_detailed' and check if the pack components are removed
        pack_order_line.of_pack_type = "non_detailed"
        self.assertEqual(len(order.order_line), 1)  # Only the pack line should be present

        # Set it back to 'detailed' and check if the pack components are added back
        pack_order_line.of_pack_type = "detailed"
        self.assertEqual(len(order.order_line), 6)  # 1 Pack line and its 5 components (including the new product)

        # Remove on item from the pack in sale order line and check that the component is removed from the pack order
        # line and the sale order line
        removed_line_knife = pack_order_line.of_pack_line_ids.filtered(
            lambda line: line.product_id == self.product_knife
        )
        pack_order_line.of_pack_line_ids -= removed_line_knife

        self.assertEqual(len(pack_order_line.of_pack_line_ids), 4)
        self.assertEqual(len(order.order_line), 5)  # 1 Pack line and its 4 components (excluding the removed component)
        self.assertFalse(  # The removed component should not be present in the sale order line
            order.order_line.filtered(
                lambda line: line.product_id == self.product_knife and line.pack_parent_line_id == pack_order_line
            )
        )

        # Add the removed item back to the pack in sale order line
        pack_order_line.of_pack_line_ids = [
            Command.create(
                {
                    "product_id": self.product_knife.id,
                    "quantity": 1.0,
                },
            ),
        ]
        self.assertTrue(  # The component should be back in the sale order line
            order.order_line.filtered(
                lambda line: line.product_id == self.product_knife and line.pack_parent_line_id == pack_order_line
            )
        )

        # Add new line stand alone line that contains the same product as one of the pack components
        order.order_line = [
            Command.create(
                {
                    "product_id": new_product.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        self.assertEqual(len(order.order_line), 7)  # 1 Stand-alone line and 1 Pack line and its 5 components

        # Then remove the pack component and check that the stand alone line is not removed
        removed_line_new_product = pack_order_line.of_pack_line_ids.filtered(
            lambda line: line.product_id == new_product
        )
        pack_order_line.of_pack_line_ids -= removed_line_new_product

        self.assertEqual(len(pack_order_line.of_pack_line_ids), 4)  # 4 components left (Spoon, Knife, Pot, Glass)
        self.assertEqual(len(order.order_line), 6)  # 1 Stand-alone line and 1 Pack line and its 4 components
        self.assertTrue(
            order.order_line.filtered(lambda line: line.product_id == new_product and not line.pack_parent_line_id)
        )

    def test_04_sale_order_line_product_uom_qty_ignored(self):
        """Test if the quantities (and the price unit) are correctly computed on the sale order lines for an ignored
        component price on pack"""
        self.pack_kitchen.pack_type = "detailed"
        self.pack_kitchen.pack_component_price = "ignored"

        order_values = self._prepare_empty_sale_order_values()

        # Add a pack
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.pack_kitchen.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)

        # We should have 5 lines: 1 pack line and 4 pack components (spoon, knife, pot, glass) with their quantities
        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[1].product_uom_qty, 3)
        self.assertEqual(order.order_line[2].product_uom_qty, 3)
        self.assertEqual(order.order_line[3].product_uom_qty, 1)
        self.assertEqual(order.order_line[4].product_uom_qty, 3)
        self.assertEqual(order.order_line[0].price_unit, 105.0)  # 10.0 * 3 + 5 * 3 + 30.0 * 1 + 10.0 * 3
        self.assertEqual(order.order_line[1].price_unit, 0)
        self.assertEqual(order.order_line[2].price_unit, 0)
        self.assertEqual(order.order_line[3].price_unit, 0)
        self.assertEqual(order.order_line[4].price_unit, 0)

        # Change the quantities of the components of the pack
        with Form(order.order_line[0], "of_sale_product_pack.of_sale_order_line_view") as line_form:
            with line_form.of_pack_line_ids.edit(0) as spoon_line_form:
                spoon_line_form.quantity = 2  # from 3 to 2
            with line_form.of_pack_line_ids.edit(1) as knife_line_form:
                knife_line_form.quantity = 1  # from 3 to 1

        # The quantities and unit price should be updated on the sale order lines
        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[1].product_uom_qty, 2)
        self.assertEqual(order.order_line[2].product_uom_qty, 1)
        self.assertEqual(order.order_line[3].product_uom_qty, 1)
        self.assertEqual(order.order_line[4].product_uom_qty, 3)
        self.assertEqual(  # Price should not change as the pack_component_price is 'ignored'
            order.order_line[0].price_unit, 105.0
        )

        # Change the number of pack
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 2
                line_form.price_unit = 200.0
            order = order_form.save()

        # The new quantities should be multiplied by the number of pack and the unit price should be updated accordingly
        self.assertEqual(order.order_line[0].product_uom_qty, 2)
        self.assertEqual(order.order_line[1].product_uom_qty, 4)
        self.assertEqual(order.order_line[2].product_uom_qty, 2)
        self.assertEqual(order.order_line[3].product_uom_qty, 2)
        self.assertEqual(order.order_line[4].product_uom_qty, 6)
        self.assertEqual(  # Price should not change as the pack_component_price is 'ignored'
            order.order_line[0].price_unit, 200.0
        )

    def test_04_sale_order_line_product_uom_qty_totalized(self):
        """Test if the quantities (and the price unit) are correctly computed on the sale order lines
        for a totalized component price on pack"""
        self.pack_kitchen.pack_type = "detailed"
        self.pack_kitchen.pack_component_price = "totalized"

        order_values = self._prepare_empty_sale_order_values()

        # Add a pack
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.pack_kitchen.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)

        # We should have 5 lines: 1 pack line and 4 pack components (spoon, knife, pot, glass) with their quantities
        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[1].product_uom_qty, 3)
        self.assertEqual(order.order_line[2].product_uom_qty, 3)
        self.assertEqual(order.order_line[3].product_uom_qty, 1)
        self.assertEqual(order.order_line[4].product_uom_qty, 3)
        self.assertEqual(order.order_line[0].price_unit, 105.0)  # 10.0 * 3 + 5 * 3 + 30.0 * 1 + 10.0 * 3
        self.assertEqual(order.order_line[1].price_unit, 0)
        self.assertEqual(order.order_line[2].price_unit, 0)
        self.assertEqual(order.order_line[3].price_unit, 0)
        self.assertEqual(order.order_line[4].price_unit, 0)

        # Change the quantities of the components of the pack
        with Form(order.order_line[0], "of_sale_product_pack.of_sale_order_line_view") as line_form:
            with line_form.of_pack_line_ids.edit(0) as spoon_line_form:
                spoon_line_form.quantity = 2  # from 3 to 2
            with line_form.of_pack_line_ids.edit(1) as knife_line_form:
                knife_line_form.quantity = 1  # from 3 to 1

        # The quantities and unit price should be updated on the sale order lines
        self.assertEqual(order.order_line[0].product_uom_qty, 1)
        self.assertEqual(order.order_line[1].product_uom_qty, 2)
        self.assertEqual(order.order_line[2].product_uom_qty, 1)
        self.assertEqual(order.order_line[3].product_uom_qty, 1)
        self.assertEqual(order.order_line[4].product_uom_qty, 3)
        self.assertEqual(order.order_line[0].price_unit, 85.0)  # 10.0 * 2 + 5.0 * 1 + 30.0 * 1 + 10.0 * 3

        # Change the number of pack
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 2
            order = order_form.save()

        # The new quantities should be multiplied by the number of pack and the unit price should be updated accordingly
        self.assertEqual(order.order_line[0].product_uom_qty, 2)
        self.assertEqual(order.order_line[1].product_uom_qty, 4)
        self.assertEqual(order.order_line[2].product_uom_qty, 2)
        self.assertEqual(order.order_line[3].product_uom_qty, 2)
        self.assertEqual(order.order_line[4].product_uom_qty, 6)
        self.assertEqual(order.order_line[0].price_unit, 85.0)  # 2 * (10.0 * 2 + 5.0 * 1 + 30.0 * 1 + 10.0 * 3)

    def test_05_sale_order_line_pricelist_with_pack(self):
        """Test the behavior of sale order lines with pricelists and product packs."""
        # Ensure the pricelist is set to advanced and the user is in the group product_pricelist to be able to use
        # advanced pricelists
        self.env["res.config.settings"].create({"product_pricelist_setting": "advanced"}).execute()
        # FIXME: Hack because it seems that the group is not correctly set in the database when configuring the
        #  pricelist settings
        pricelist_group = self.env.ref("product.group_product_pricelist")
        self.env.user.write({"groups_id": [Command.link(pricelist_group.id)]})

        # Add Glass to the Kitchen pack
        self.pack_kitchen.pack_line_ids = [
            Command.create(
                {
                    "product_id": self.product_glass.id,
                    "quantity": 1.0,
                },
            ),
        ]

        # Create a sale order with the pack
        order_values = self._prepare_empty_sale_order_values()
        with Form(self.env["sale.order"].create(order_values)) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.pack_kitchen
            order = order_form.save()

        kitchen_line = order.order_line.filtered(lambda kl: kl.product_id == self.pack_kitchen)

        # As we didn't set any custom pricelist, the default pricelist should be applied to the pack components
        # with their original prices
        self.assertEqual(kitchen_line.of_pack_line_ids[0].price_unit, 10.0)  # Spoon
        self.assertEqual(kitchen_line.of_pack_line_ids[1].price_unit, 5.0)  # Knife
        self.assertEqual(kitchen_line.of_pack_line_ids[2].price_unit, 30.0)  # Pot
        self.assertEqual(kitchen_line.of_pack_line_ids[3].price_unit, 10.0)  # Fork
        self.assertEqual(kitchen_line.of_pack_line_ids[4].price_unit, 27.0)  # Glass
        self.assertEqual(
            kitchen_line.price_unit, sum(pl.price_unit * pl.quantity for pl in kitchen_line.of_pack_line_ids)
        )
        self.assertEqual(kitchen_line.price_unit, 132.0)

        # Change the pricelist to the kitchen pricelist (with 5% on the Spoon and 10% on the Pot, 15 fixed price on the
        # Glass and 5 fixed price on the Fork category)
        with Form(order) as order_form:
            order_form.pricelist_id = self.pricelist_kitchen
            order = order_form.save()
            order.action_update_prices()

        # Pack components should have the prices set in the pricelist
        self.assertEqual(kitchen_line.of_pack_line_ids[0].price_unit, 9.5)  # Spoon
        self.assertEqual(kitchen_line.of_pack_line_ids[1].price_unit, 5.0)  # Knife
        self.assertEqual(kitchen_line.of_pack_line_ids[2].price_unit, 27.0)  # Pot
        self.assertEqual(kitchen_line.of_pack_line_ids[3].price_unit, 5.0)  # Fork
        self.assertEqual(kitchen_line.of_pack_line_ids[4].price_unit, 15.0)  # Glass
        self.assertEqual(
            kitchen_line.price_unit, sum(pl.price_unit * pl.quantity for pl in kitchen_line.of_pack_line_ids)
        )
        # Sale order line price should be the sum of the pack components
        self.assertEqual(kitchen_line.price_unit, 100.5)

        # Change the pricelist to the kitchen pricelist with a 25% discount on the Pot
        with Form(order) as order_form:
            order_form.pricelist_id = self.pricelist_kitchen_25perc
            # add a new line with a pot that should have a 25% discount
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.product_pot
            # add a new line with a glass that should not have any discount
            with order_form.order_line.new() as line_form:
                line_form.product_id = self.product_glass
            order = order_form.save()

        # New added lines should have the prices set in the pricelist with the discount applied on the Pot and not on
        # the Glass
        self.assertEqual(order.order_line[1].price_unit, 22.5)  # Pot
        self.assertEqual(order.order_line[2].price_unit, 27.0)  # Glass (original price, no discount)

    def test_06_unlink_allowed(self):
        """Test that we can't unlink a pack line if the sale order is not in draft or sent state"""
        order_values = self._prepare_empty_sale_order_values()
        order_values["order_line"] = [
            Command.create(
                {
                    "product_id": self.pack_kitchen.id,
                    "product_uom_qty": 1,
                },
            ),
        ]
        order = self.env["sale.order"].create(order_values)

        self.assertEqual(order.order_line[0].of_pack_ok, True)
        self.assertEqual(len(order.order_line[0].of_pack_line_ids), 4)

        order.order_line[0].of_pack_line_ids[0].unlink()
        self.assertEqual(len(order.order_line[0].of_pack_line_ids), 3)

        # Change the status of the sale order to 'sale' and try to delete a pack line
        order.action_confirm()
        with self.assertRaises(UserError):
            order.order_line[0].of_pack_line_ids[0].unlink()

        self.assertEqual(len(order.order_line[0].of_pack_line_ids), 3)

        # Change the status of the sale order to 'cancel' and try to delete a pack line
        order.with_context(disable_cancel_warning=True).action_cancel()
        self.assertEqual(order.state, "cancel")
        with self.assertRaises(UserError):
            order.order_line[0].of_pack_line_ids[0].unlink()

        self.assertEqual(len(order.order_line[0].of_pack_line_ids), 3)
