# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_equipment.tests.common import TestOFEquipmentCommon


class TestOFStockPicking(TestOFEquipmentCommon):
    def setUp(self):
        super().setUp()

        # Create Equipment
        self.lot_wood_stove = self.env['stock.lot'].create(
            {'name': "LOT/WS00001", 'product_id': self.product_wood_stove.id}
        )

        # Create Sale Order used in the tests
        self.order = self.env['sale.order'].create(
            {
                'partner_id': self.customer_a.id,
                'order_line': [
                    Command.create({'product_id': self.product_wood_stove.id, 'product_uom_qty': 1}),
                    Command.create({'product_id': self.product_ash_vacuum_cleaner.id, 'product_uom_qty': 1}),
                ],
            }
        )
        self.order.action_confirm()

        # Process quantities and assign a lot to the wood stove product move line
        self.picking = self.order.picking_ids[-1]
        self.picking.move_ids_without_package.write({'quantity_done': 1})
        self.picking.move_line_nosuggest_ids.filtered(lambda m: m.product_id == self.product_wood_stove).write(
            {
                'lot_id': self.lot_wood_stove.id,
            }
        )

    def check_existing_lot_equipment(self, picking, arg1):
        lot_equipment = self.env['of.equipment'].search(
            [
                ('name', '=', f"{self.lot_wood_stove.name} - {picking.partner_id.name}"),
                ('customer_id', '=', picking.partner_id.id),
                ('product_id', '=', self.product_wood_stove.id),
                ('lot_id', '=', self.lot_wood_stove.id),
            ]
        )
        self.assertEqual(len(lot_equipment), arg1)

    def test_01_create_equipment_on_picking_confirmation_ok(self):
        """
        Test case to verify that equipment is created when picking is confirmed.

        Steps:
        1. Enable the 'group_stock_production_lot' and 'of_equipment_auto_create' settings.
        2. Check that no equipment exists before confirming the picking.
        3. Confirm the picking.
        4. Check that an equipment has been created after confirming the picking.

        Expected result:
        - An equipment should be created during the process.
        """
        self.env['res.config.settings'].create(
            {'group_stock_production_lot': True, 'of_equipment_auto_create': True}
        ).execute()

        # No equipment should be existing yet
        self.check_existing_lot_equipment(self.picking, 0)
        # Confirm the picking
        self.picking.button_validate()
        # An equipment should have been created
        self.check_existing_lot_equipment(self.picking, 1)

    def test_02_create_equipment_on_picking_confirmation_nok(self):
        """
        Test case to verify that no equipment is created when picking confirmation fails.

        Steps:
        1. Set the configuration settings to disable automatic creation of equipment.
        2. Confirm the order.
        3. Check that no equipment exists before picking confirmation.
        4. Validate the picking.
        5. Check that no equipment is created after picking confirmation.

        Expected result:
        - No equipment should be created during the process.

        """
        self.env['res.config.settings'].create(
            {'group_stock_production_lot': True, 'of_equipment_auto_create': False}
        ).execute()

        self.order.action_confirm()

        # No equipment should be existing yet
        self.check_existing_lot_equipment(self.picking, 0)
        # Confirm the picking
        self.picking.button_validate()
        # No equipment should have been created
        self.check_existing_lot_equipment(self.picking, 0)
