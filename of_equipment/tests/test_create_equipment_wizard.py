# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import Form

from odoo.addons.of_equipment.tests.common import TestOFEquipmentCommon


class TestOFEquipmentWizard(TestOFEquipmentCommon):
    def setUp(self):
        return super().setUp()

    def test_01_create_equipment_wizard_sale(self):
        """Test case for creating equipment wizard for sale order.

        This test case creates a sale order with a product, confirms the order,
        and then creates a new equipment wizard for the order. It checks that
        the order has no equipment before creating the wizard, and that the order
        has one equipment after creating and validating the wizard. It also checks that the
        equipment has the correct data.
        """
        order = self.env['sale.order'].create(
            {
                'partner_id': self.customer_a.id,
                'company_id': self.company_fr.id,
                'order_line': [
                    Command.create(
                        {
                            'product_id': self.product_wood_stove.id,
                            'product_uom_qty': 1,
                            'price_unit': 1000,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        # Check that the order has no equipment
        self.assertEqual(len(order.of_equipment_ids), 0)
        # Create a new equipment wizard
        with Form(
            self.env['of.create.equipment.wizard'].with_context(active_id=order.id, active_model='sale.order')
        ) as wizard_form:
            wizard_form.name = "CA/WS00001"
            wizard_form.product_id = self.product_wood_stove
            wizard_create_equipment = wizard_form.save()
        wizard_create_equipment.action_button_create_equipment()
        # Check that the order has now one equipment
        self.assertTrue(len(order.of_equipment_ids), 1)
        equipment = order.of_equipment_ids[-1]
        # Check that the equipment has the correct data
        self.assertEqual(equipment.product_id, self.product_wood_stove)
        self.assertEqual(equipment.service_date, order.date_order.date())
        self.assertEqual(equipment.customer_id, order.partner_id)
        self.assertEqual(equipment.reseller_id, order.company_id.partner_id)
        self.assertEqual(equipment.installer_id, order.company_id.partner_id)

    def test_02_create_equipment_wizard_move(self):
        """Test case for creating equipment wizard for invoice.

        This test case creates an invoice with a product, validates the invoice,
        and then creates a new equipment wizard for the invoice. It checks that
        the invoice has no equipment before creating the wizard, and that the invoice
        has one equipment after creating and validating the wizard. It also checks that the
        equipment has the correct data.
        """
        move = self.env['account.move'].create(
            {
                'partner_id': self.customer_a.id,
                'company_id': self.company_fr.id,
                'invoice_line_ids': [
                    Command.create(
                        {
                            'product_id': self.product_wood_stove.id,
                            'quantity': 1,
                            'price_unit': 1000,
                        }
                    )
                ],
            }
        )
        move.action_post()
        # Check that the invoice has no equipment
        self.assertEqual(len(move.of_equipment_ids), 0)
        # Create a new equipment wizard
        with Form(
            self.env['of.create.equipment.wizard'].with_context(active_id=move.id, active_model='account.move')
        ) as wizard_form:
            wizard_form.name = "CA/WS00001"
            wizard_form.product_id = self.product_wood_stove
            wizard_create_equipment = wizard_form.save()
        wizard_create_equipment.action_button_create_equipment()
        # Check that the invoice has now one equipment
        self.assertTrue(len(move.of_equipment_ids), 1)
        equipment = move.of_equipment_ids[-1]
        # Check that the equipment has the correct data
        self.assertEqual(equipment.product_id, self.product_wood_stove)
        self.assertEqual(equipment.service_date, move.invoice_date)
        self.assertEqual(equipment.customer_id, move.partner_id)
        self.assertEqual(equipment.reseller_id, move.company_id.partner_id)
        self.assertEqual(equipment.installer_id, move.company_id.partner_id)
