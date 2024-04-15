# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestCalendarEvent(TestOFPlanningCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['calendar.event'].create(
            {
                'name': 'Test Event',
                'of_type': 'intervention',
                'start': fields.Datetime.now(),
                'of_company_id': cls.company_fr.id,
                'of_employee_ids': [Command.set([cls.employee_tech_johnny.id])],
                'of_partner_id': cls.customer_a.id,
            }
        )
        cls.warehouse_1 = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_fr.id)], limit=1)

    def test_01_employees_capabilities_nok(self):
        dt_now = fields.Datetime.now()
        with self.assertRaises(ValidationError):  # Jean does not know how to install a stove
            with Form(
                self.env['calendar.event'].with_context(
                    default_of_type='intervention',
                    default_start=dt_now,
                    default_of_company_id=self.company_fr.id,
                )
            ) as event_form:
                event_form.name = 'Test Event'
                event_form.of_template_id = self.template_installation
                event_form.of_employee_ids.add(self.employee_tech_jean)

    def test_02_employees_capabilities_ok(self):
        dt_now = fields.Datetime.now()
        with Form(
            self.env['calendar.event'].with_context(
                default_of_type='intervention',
                default_start=dt_now,
                default_of_company_id=self.company_fr.id,
            )
        ) as event_form:
            event_form.name = 'Test Event'
            event_form.of_template_id = self.template_installation
            event_form.of_employee_ids.add(self.employee_tech_bruce)
            event_form.save()

        event_form.of_employee_ids.clear()
        event_form.of_employee_ids.add(self.employee_tech_bruce)

    def test_03_employees_capabilities_both_one_is_ok(self):
        dt_now = fields.Datetime.now()
        with Form(
            self.env['calendar.event'].with_context(
                default_of_type='intervention',
                default_start=dt_now,
                default_of_company_id=self.company_fr.id,
            )
        ) as event_form:
            event_form.name = 'Test Event'
            event_form.of_template_id = self.template_installation
            event_form.of_employee_ids.add(self.employee_tech_jean)
            event_form.of_employee_ids.add(self.employee_tech_bruce)

    def test_04_action_generate_stock_picking_no_product(self):
        """
        Test case to check if an exception is raised when there are no products to deliver in the intervention.
        """
        with self.assertRaises(UserError) as error:
            self.event.action_generate_stock_picking()
        self.assertEqual(error.exception.args[0], "Aucun produit à livrer dans l'intervention.")

    def test_05_action_generate_stock_picking_multiple_events(self):
        """
        Test case to verify the behavior of the 'action_generate_stock_picking' method
        when multiple events are selected.

        It creates two calendar events with the same company, partner and type, and then tries
        to generate stock picking for both events. It expects a UserError to be raised
        with the message "Aucun produit à livrer dans les interventions sélectionnées."
        """
        event1 = self.env['calendar.event'].create(
            {
                'name': 'Event 1',
                'of_type': 'intervention',
                'start': fields.Datetime.now(),
                'stop': fields.Datetime.now() + timedelta(hours=1),
                'of_company_id': self.company_fr.id,
                'of_partner_id': self.customer_a.id,
            }
        )
        event2 = self.env['calendar.event'].create(
            {
                'name': 'Event 2',
                'of_type': 'intervention',
                'start': fields.Datetime.now(),
                'stop': fields.Datetime.now() + timedelta(hours=1),
                'of_company_id': self.company_fr.id,
                'of_partner_id': self.customer_a.id,
            }
        )

        with self.assertRaises(UserError) as error:
            self.env['calendar.event'].browse([event1.id, event2.id]).action_generate_stock_picking()
        self.assertEqual(error.exception.args[0], "Aucun produit à livrer dans les interventions sélectionnées.")

    def test_06_action_generate_stock_picking_with_product(self):
        """
        Test case for the action_generate_stock_picking method when a product is present.

        This test verifies that the action_generate_stock_picking method behaves correctly when a product is added to
        the intervention line.
        It checks that a stock picking is generated, the picking's state is confirmed, and the correct product is
        included in the picking.
        """
        self.env['res.config.settings'].create(
            {
                'group_intervention_use_deliveries': True,
            }
        ).execute()

        # On ajoute une ligne de facturation
        self.event.of_invoice_policy = 'delivery'
        self.env['of.planning.intervention.line'].create(
            {
                'intervention_id': self.event.id,
                'product_id': self.product_ash_vacuum_cleaner.id,
                'qty': 1,
            }
        )
        self.event.action_button_confirm()

        # La génération d'un BL nécessite le renseignement d'un entrepôt
        with self.assertRaises(UserError) as error:
            self.event.action_generate_stock_picking()
        self.assertEqual(
            error.exception.args[0],
            f"Veuillez renseigner un entrepôt dans l'onglet Facturation de l'intervention: {self.event.name}",
        )
        self.event.of_warehouse_id = self.warehouse_1

        # Un premier BL est généré
        self.event.action_generate_stock_picking()
        self.assertEqual(len(self.event.of_picking_ids), 1)
        self.assertEqual(self.event.of_picking_ids[0].state, 'confirmed')
        self.assertEqual(len(self.event.of_picking_ids[0].move_ids_without_package), 1)
        self.assertEqual(
            self.event.of_picking_ids[0].move_ids_without_package[0].product_id, self.product_ash_vacuum_cleaner
        )

        self.env['of.planning.intervention.line'].create(
            {
                'intervention_id': self.event.id,
                'product_id': self.product_wood_stove.id,
                'qty': 1,
            }
        )

        # Une ligne est ajouté au premier BL
        self.event.action_generate_stock_picking()
        self.assertEqual(len(self.event.of_picking_ids), 1)
        self.assertEqual(self.event.of_picking_ids[0].state, 'confirmed')
        self.assertEqual(len(self.event.of_picking_ids[0].move_ids_without_package), 2)
        self.assertEqual(self.event.of_picking_ids[0].move_ids_without_package[1].product_id, self.product_wood_stove)

        # Rien a ajouter au BL existant
        with self.assertRaises(UserError) as error:
            self.event.action_generate_stock_picking()
        self.assertEqual(
            error.exception.args[0],
            f"Aucun article à ajouter dans un bon de livraison: {[self.event.name]}",
        )

        # On confirme le premier BL
        self.event.of_picking_ids[0].move_ids_without_package[0].quantity_done = 1
        self.event.of_picking_ids[0].move_ids_without_package[1].quantity_done = 1
        self.event.of_picking_ids[0].button_validate()
        self.assertEqual(self.event.of_picking_ids[0].state, 'done')

        # On rajoute une ligne de facturation, on regénère un BL.
        # Un nouveau BL doit être généré car le premier est confirmé
        self.env['of.planning.intervention.line'].create(
            {
                'intervention_id': self.event.id,
                'product_id': self.product_wood_stove.id,
                'qty': 1,
            }
        )
        self.event.action_generate_stock_picking()
        self.assertEqual(len(self.event.of_picking_ids), 2)
        self.assertEqual(self.event.of_picking_ids[1].state, 'confirmed')
        self.assertEqual(len(self.event.of_picking_ids[1].move_ids_without_package), 1)
        self.assertEqual(self.event.of_picking_ids[1].move_ids_without_package[0].product_uom_qty, 1)

    def test_07_action_create_invoice(self):
        """
        Test case for the action_create_invoice method of the calendar.event model.

        This test verifies the behavior of the action_create_invoice method when creating an invoice from a calendar
        event.

        Steps:
        1. Create a calendar event with required fields.
        2. Verify that an error is raised when there is no fiscal position selected.
        3. Set a fiscal position and verify that a popup wizard is returned with a failure message when there are no
            invoiceable lines.
        4. Set a template and confirm the event.
        5. Verify that a popup wizard is returned with a success message when creating an invoice.
        6. Verify the created invoice and its invoice lines.
        7. Try to create another invoice and verify that a popup wizard is returned with a failure message.
        8. Add a new line to the event that is falsely linked to a sale order line.
        9. Try to create an invoice and verify that a popup wizard is returned with a failure message.
        10. Unlink the false order lines and try to create an invoice again.
        11. Verify that a popup wizard is returned with a success message when creating an invoice.
        12. Verify the newly created invoice and its invoice lines.
        """

        # No fiscal position
        # with self.assertRaises(ValidationError) as create_invoice_error:
        self.event.of_fiscal_position_id = False
        self._assert_invoice_create_result(
            "<p>La facturation n'a pas pu être complétée car :<br/><ul><li>L'intervention n'est pas facturable, "
            "veuillez sélectionner une position fiscale.</li></ul><p>",
        )
        self.event.of_fiscal_position_id = self.fiscal_pos_20

        self._assert_invoice_create_result(
            "<p>La facturation n'a pas pu être complétée car :<br/><ul><li>L'intervention n'est pas facturable car elle"
            " doit être confirmée.</li><li>Il n'y a pas de ligne de facturation présente dans l'intervention."
            "</li></ul><p>",
        )

        # Confirm the event to be able to invoice it but there is no line to invoice, so it should fail
        self.event.action_button_confirm()
        self._assert_invoice_create_result(
            "<p>La facturation n'a pas pu être complétée car :<br/><ul><li>Il n'y a pas de ligne de facturation "
            "présente dans l'intervention.</li></ul><p>",
        )

        # Add a line to invoice from the template
        self.event.of_template_id = self.template_installation

        # Confirm the event to be able to invoice it
        self.event.action_button_confirm()
        self._assert_invoice_create_result("Facture créée avec succès.")

        # Check the invoice
        self.assertEqual(len(self.event.of_invoice_ids), 1)
        self.assertRecordValues(
            self.event.of_invoice_ids,
            [{'state': 'draft', 'amount_untaxed': 125.0, 'amount_tax': 25.0, 'amount_total': 150.0}],
        )
        self.assertEqual(len(self.event.of_invoice_ids.invoice_line_ids), 1)
        self.assertRecordValues(
            self.event.of_invoice_ids.invoice_line_ids,
            [{'product_id': self.product_ash_vacuum_cleaner.id, 'quantity': 1, 'price_unit': 125.0}],
        )
        self._assert_invoice_create_result(
            "<p>La facturation n'a pas pu être complétée car :<br/><ul><li>Il n'y a pas de ligne de facturation "
            "présente dans l'intervention.</li></ul><p>",
        )

        # Add a new line falsy linked to a sale order line that should not be invoiced
        false_order = self.env['sale.order'].create(
            {
                'partner_id': self.customer_a.id,
                'fiscal_position_id': self.fiscal_pos_20.id,
                'order_line': [
                    Command.create(
                        {
                            'product_id': self.product_wood_stove.id,
                            'product_uom_qty': 1,
                            'price_unit': 125.0,
                        },
                    )
                ],
            }
        )
        self.event.write(
            {
                'of_line_ids': [
                    Command.create(
                        {
                            'product_id': self.product_ash_vacuum_cleaner.id,
                            'qty': 1,
                            'price_unit': 125.0,
                            'order_line_id': false_order.order_line[0].id,
                        }
                    )
                ]
            }
        )
        self._assert_invoice_create_result(
            "<p>La facturation n'a pas pu être complétée car :<br/><ul><li>Il n'y a pas de ligne de facturation "
            "présente dans l'intervention.</li></ul><p>",
        )

        # Unlink false order lines and try to invoice again
        false_order.with_context(disable_cancel_warning=True).action_cancel()
        false_order.unlink()

        # Force recomputation of invoiceable quantity and invoice status because of the unlink of the false order
        self.event.of_line_ids._compute_qty_invoiceable()
        self.event.of_line_ids._compute_invoice_status()
        self._assert_invoice_create_result("Facture créée avec succès.")
        self.assertEqual(len(self.event.of_invoice_ids), 2)
        self.assertRecordValues(
            self.event.of_invoice_ids,
            [
                {'state': 'draft', 'amount_untaxed': 125.0, 'amount_tax': 25.0, 'amount_total': 150.0},
                {'state': 'draft', 'amount_untaxed': 125.0, 'amount_tax': 25.0, 'amount_total': 150.0},
            ],
        )
        self.assertEqual(len(self.event.of_invoice_ids.invoice_line_ids), 2)

    def _assert_invoice_create_result(self, message):
        result = self.event.action_create_invoice()
        self.assertIsInstance(result, dict)
        self.assertEqual(result['res_model'], 'of.popup.wizard')
        self.assertEqual(result['context']['default_message_html'], message)
