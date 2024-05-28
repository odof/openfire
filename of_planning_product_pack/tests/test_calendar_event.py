# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.tests.common import Form

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestOFPlanningProductPack(TestOFPlanningCommon):
    def setUp(self):
        return super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wood_log = cls.create_product(
            {
                "name": "Bûche de bois",
                "default_code": "LOG_001",
                "list_price": 10,
                "categ_id": cls.env.ref("product.product_category_all").id,
                "type": "product",
                "expense_policy": "no",
            }
        )

        cls.product_pack_wood_stove = cls.env["product.product"].create(
            {
                "name": "KIT Poêle à bois",
                "default_code": "BA_PACK_001",
                "brand_id": cls.brand_stove.id,
                "categ_id": cls.env.ref("product.product_category_all").id,
                "pack_ok": True,
                "pack_type": "detailed",
                "pack_component_price": "totalized",
                "standard_price": 1500,
                "list_price": 2750,
                "type": "product",
                "pack_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_wood_stove.id,
                            "quantity": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.wood_log.id,
                            "quantity": 3,
                        }
                    ),
                ],
            }
        )

    def test_00_planning_product_pack_qty_delivered(self):
        """The delivered quantity of a product pack on an event should be correctly computed.

        The event is created with a product pack ("KIT Poêle à bois") and a quantity of 2.
        This pack contains 1 "Poêle à bois" and 3 "Bûches de bois."
        The event is confirmed with 2 "KIT Poêle à bois."
        The first picking is validated with 2 "Poêles à bois" and 4 "Bûches de bois" so we should have 1 delivered pack
        and 1 backorder pack.

        The second picking is validated with 2 "Bûches de bois."
        The event should now have 2 delivered packs.
        """
        # Create an event with a product pack
        with Form(self.env["calendar.event"], view="of_planning.calendar_event_view_form") as event_form:
            event_form.name = "Test Event"
            event_form.of_force_dates = True
            event_form.start = fields.Datetime.now().replace(hour=9, minute=0, second=0)
            event_form.of_address_id = self.partner_bruce
            event_form.of_task_id = self.task_installation
            event_form.duration = 1.5
            event_form.of_warehouse_id = self.warehouse_1
            with event_form.of_line_ids.new() as line_form:
                line_form.product_id = self.product_pack_wood_stove
                line_form.qty = 2
        event = event_form.save()

        # Confirm the event to create the picking
        event.action_button_confirm()
        self.assertEqual(len(event.of_picking_ids), 1)
        first_picking = event.of_picking_ids[0]
        self.assertEqual(len(first_picking.move_ids_without_package), 2)
        self.assertRecordValues(
            first_picking.move_ids_without_package,
            [
                {"product_id": self.product_wood_stove.id, "product_uom_qty": 2},
                {"product_id": self.wood_log.id, "product_uom_qty": 6},
            ],
        )

        # Validate the first picking with 2 "Poêles à bois" and 4 "Bûches de bois"
        with Form(first_picking) as picking_form:
            with picking_form.move_ids_without_package.edit(0) as line:
                line.quantity_done = 2
            with picking_form.move_ids_without_package.edit(1) as line:
                line.quantity_done = 4
        first_picking = picking_form.save()
        action_data = first_picking.button_validate()
        backorder_wizard = Form(self.env["stock.backorder.confirmation"].with_context(**action_data["context"])).save()
        backorder_wizard.process()

        # The event should have 1 delivered pack and 1 pack to deliver
        self.assertEqual(len(event.of_picking_ids), 2)
        self.assertEqual(event.of_line_ids[0].qty_delivered, 1)

        # Validate the second picking with 2 "Bûches de bois"
        second_picking = event.of_picking_ids[1]
        self.assertEqual(len(second_picking.move_ids_without_package), 1)
        with Form(second_picking) as picking_form:
            with picking_form.move_ids_without_package.edit(0) as line:
                line.quantity_done = 2
        action_data = second_picking.button_validate()

        # The event should now have 2 delivered packs
        self.assertEqual(event.of_line_ids[0].qty_delivered, 2)
