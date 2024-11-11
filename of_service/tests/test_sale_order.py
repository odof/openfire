# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import Form

from odoo.addons.of_service.tests.common import TestOFServiceCommon


class TestOFServiceRequestSaleOrder(TestOFServiceCommon):
    def _create_sale_order_and_check_message(self, request, message):
        """Create a sale order and check that the message is correct
        :param message: The expected message
        """
        result = request._make_sale_order()
        self.assertIsInstance(result, dict)
        self.assertIn("res_model", result)
        self.assertEqual(result["res_model"], "of.popup.wizard")
        self.assertIn("context", result)
        self.assertEqual(result["context"]["default_message"], message)

    def _make_fake_invoice(self, request):
        """Create fake invoice to test the method _make_sale_order"""
        self.env["account.move"].create(
            {
                "partner_id": request.partner_id.id,
                "company_id": request.company_id.id,
                "move_type": "out_invoice",
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": line.name,
                            "quantity": line.qty,
                            "price_unit": line.price_unit,
                            "product_id": line.product_id.id,
                            "of_request_line_id": line.id,
                        }
                    )
                    for line in request.line_ids
                ],
            }
        )

    def test_01_make_so_base_state(self):
        """Test that the method _make_sale_order returns a message when the base_state is not 'calculated'"""
        request = self.env["of.service.request"].create(
            {
                "partner_id": self.partner_tony.id,
                "address_id": self.partner_tony.id,
                "task_id": self.task_sweeping.id,
                "type_id": self.env.ref("of_service.of_service_request_type_technical").id,
                "company_id": self.company_fr.id,
                "fiscal_position_id": self.fiscal_pos_20.id,
                "next_date": fields.Date.today(),
                "end_date": fields.Date.today() + relativedelta(days=15),
            }
        )
        self._create_sale_order_and_check_message(request, "Cette demande d'intervention n'est pas validée.")

    def test_02_make_so_no_lines(self):
        """Test that the method _make_sale_order returns a message when the service request has no lines"""
        request = self.env["of.service.request"].create(
            {
                "partner_id": self.partner_tony.id,
                "address_id": self.partner_tony.id,
                "task_id": self.task_sweeping.id,
                "type_id": self.env.ref("of_service.of_service_request_type_technical").id,
                "company_id": self.company_fr.id,
                "fiscal_position_id": self.fiscal_pos_20.id,
                "next_date": fields.Date.today(),
                "end_date": fields.Date.today() + relativedelta(days=15),
                "base_state": "calculated",
            }
        )
        self._create_sale_order_and_check_message(request, "Cette demande d'intervention n'a pas de lignes.")

    def test_03_make_so_associated_lines(self):
        """Test that the method _make_sale_order returns a message when all the lines are already associated
        to a sale order"""
        with Form(
            self.env["of.service.request"].create(
                {
                    "partner_id": self.partner_tony.id,
                    "address_id": self.partner_tony.id,
                    "type_id": self.env.ref("of_service.of_service_request_type_installation").id,
                    "task_id": self.task_sweeping.id,
                    "company_id": self.company_fr.id,
                    "fiscal_position_id": self.fiscal_pos_20.id,
                    "next_date": fields.Date.today(),
                    "end_date": fields.Date.today() + relativedelta(days=15),
                }
            )
        ) as request_form:
            request_form.template_id = self.template_installation
            request = request_form.save()
        # Set the base_state to 'calculated' to be able to create a sale order
        request.base_state = "calculated"
        # Create a sale order to associate the lines
        result = request._make_sale_order()
        self.assertIsInstance(result, dict)
        self.assertIn("res_model", result)
        self.assertIn("res_id", result)
        self.assertEqual(result["res_model"], "sale.order")
        # Create a new sale order
        self._create_sale_order_and_check_message(request, "Toutes les lignes sont déjà associées à une commande.")

    def test_04_make_so_no_fiscal_position(self):
        """Test that the method _make_sale_order returns a message when the fiscal position is not set"""
        with Form(
            self.env["of.service.request"].create(
                {
                    "partner_id": self.partner_tony.id,
                    "address_id": self.partner_tony.id,
                    "type_id": self.env.ref("of_service.of_service_request_type_installation").id,
                    "task_id": self.task_sweeping.id,
                    "company_id": self.company_fr.id,
                    "fiscal_position_id": self.fiscal_pos_20.id,
                    "next_date": fields.Date.today(),
                    "end_date": fields.Date.today() + relativedelta(days=15),
                }
            )
        ) as request_form:
            request_form.template_id = self.template_installation
            request = request_form.save()
        # Set the base_state to 'calculated' to be able to create a sale order
        request.base_state = "calculated"
        # Remove the fiscal position
        request.fiscal_position_id = False
        # Create a sale order
        self._create_sale_order_and_check_message(request, "Veuillez saisir une position fiscale.")

    def test_05_make_so_invoiced_lines(self):
        """Test that the method _make_sale_order returns a message when all the lines are already invoiced"""
        with Form(
            self.env["of.service.request"].create(
                {
                    "partner_id": self.partner_tony.id,
                    "address_id": self.partner_tony.id,
                    "type_id": self.env.ref("of_service.of_service_request_type_installation").id,
                    "task_id": self.task_sweeping.id,
                    "company_id": self.company_fr.id,
                    "fiscal_position_id": self.fiscal_pos_20.id,
                    "next_date": fields.Date.today(),
                    "end_date": fields.Date.today() + relativedelta(days=15),
                }
            )
        ) as request_form:
            request_form.template_id = self.template_installation
            request = request_form.save()
        # Set the base_state to 'calculated' to be able to create a sale order
        request.base_state = "calculated"
        # Prepare false invoice line to check that the method _make_sale_order returns a message
        self._make_fake_invoice(request)
        # Create a new sale order
        self._create_sale_order_and_check_message(
            request, "Toutes les lignes sont déjà associées à une ou plusieurs factures."
        )

    def test_06_create_sr_on_confirmation(self):
        """Test creation of a service request if sale order template is correctly configured"""
        sale_template = self.env["sale.order.template"].create(
            {
                "name": "Test template",
                "of_order_type_id": self.env.ref("sale_order_type.normal_sale_type").id,
                "of_service_mgmt": "no",
                "of_intervention_template_id": False,
                "of_fiscal_position_id": self.fiscal_pos_20,
                "sale_order_template_line_ids": [
                    Command.create({"product_id": self.product_consu_a.id, "product_uom_qty": 1}),
                    Command.create({"product_id": self.product_consu_b.id, "product_uom_qty": 2}),
                ],
            }
        )
        order_values = self._prepare_empty_sale_order_values()
        with Form(self.env["sale.order"].create(order_values)) as order_form:
            order_form.sale_order_template_id = sale_template
            order = order_form.save()

        self.assertEqual(len(order.of_request_ids), 0)

        order.action_confirm()

        # There is no SR created here, `of_service_mgmt` is set to  `no`
        self.assertEqual(len(order.of_request_ids), 0)

        order2_values = self._prepare_empty_sale_order_values()
        # Add an intervention template and allow creation of SR
        sale_template.of_service_mgmt = "sale"
        sale_template.of_intervention_template_id = self.template_installation
        with Form(self.env["sale.order"].create(order2_values)) as order2_form:
            order2_form.sale_order_template_id = sale_template
            order2 = order2_form.save()

        order2.action_confirm()

        # We should have one SR here
        self.assertEqual(len(order2.of_request_ids), 1)
