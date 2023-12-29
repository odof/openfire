# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import Form

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestEstimatedInvoicingDate(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_of_estimated_invoicing_date(self):
        """Test the estimated invoicing date with a fixed invoice date.
        The estimated invoicing date should be the same as the fixed invoice date.
        """
        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        self.assertEqual(order.of_estimated_invoicing_date, False)

        order.of_fixed_invoice_date = datetime.now().date() + timedelta(days=7)

        order._compute_of_estimated_invoicing_date()
        self.assertEqual(order.of_estimated_invoicing_date, order.of_fixed_invoice_date)

    def test_02_of_estimated_invoicing_date_with_fixed_date(self):
        """Test the estimated invoicing date with a fixed invoice date and invoice policy 'order'
        The estimated invoicing date should be the same as the fixed invoice date.
        """
        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        self.assertEqual(order.of_estimated_invoicing_date, False)

        order.of_invoice_policy = 'order'
        order.of_fixed_invoice_date = datetime.now().date() + timedelta(days=7)

        order._compute_of_estimated_invoicing_date()
        self.assertEqual(order.of_estimated_invoicing_date, order.of_fixed_invoice_date)

    def test_03_of_estimated_invoicing_date_with_fixed_date(self):
        """Test the estimated invoicing date with a fixed invoice date and invoice policy 'delivery'.
        The estimated invoicing date should be the same as the fixed invoice date even if there are waiting pickings."""
        order = self.env['sale.order'].create(self._prepare_sale_order_values(dict(quantity=3)))
        order.of_fixed_invoice_date = datetime.now().date() + timedelta(days=14)
        order.of_invoice_policy = 'delivery'
        order.action_verification_confirm()
        self.assertEqual(len(order.picking_ids), 1, "The sale order should have one picking")

        # Check that the estimated invoicing date is the same as the fixed invoice date
        self.assertEqual(order.of_estimated_invoicing_date, order.of_fixed_invoice_date)

        # Confirm the delivery with a missing quantity to generate a backorder
        first_picking = order.picking_ids[0]
        first_picking.move_line_ids[0].qty_done = 1
        backorder_wizard_dict = first_picking.button_validate()
        backorder_wizard = Form(
            self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])
        ).save()
        backorder_wizard.process()
        self.assertEqual(len(order.picking_ids), 2, "The sale order should have two pickings")

        first_backorder = order.picking_ids.filtered(lambda p: p.backorder_id)

        # Easy way to simulate a second picking/backorder linked to the sale order to test the estimated invoicing date
        first_backorder.copy()

        # Update the scheduled date of the first picking to simulate a delay
        first_backorder.scheduled_date = first_backorder.scheduled_date + timedelta(days=7)
        self.assertEqual(
            order.of_estimated_invoicing_date,
            order.of_fixed_invoice_date,
            "The estimated invoicing date should be the same as the fixed invoice date",
        )

    def test_04_of_estimated_invoicing_date_without_fixed_date(self):
        """Test the estimated invoicing date without a fixed invoice date.
        The estimated invoicing date should be equal to the date of the closest scheduled date of pickings linked
        to the sale order.
        """
        order = self.env['sale.order'].create(self._prepare_sale_order_values(dict(quantity=3)))
        order.of_invoice_policy = 'delivery'
        order.action_verification_confirm()
        self.assertEqual(len(order.picking_ids), 1, "The sale order should have one picking")

        # Confirm the delivery with a missing quantity to generate a backorder
        first_picking = order.picking_ids[0]
        first_picking.move_line_ids[0].qty_done = 1
        backorder_wizard_dict = first_picking.button_validate()
        backorder_wizard = Form(
            self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])
        ).save()
        backorder_wizard.process()
        self.assertEqual(len(order.picking_ids), 2, "The sale order should have two pickings")

        first_backorder = order.picking_ids.filtered(lambda p: p.backorder_id)

        # Easy way to simulate a second picking linked to the sale order.
        # As we just want another picking to filter them we don't take care about data here.
        copied_picking = first_backorder.copy()

        # Update the scheduled date of the first picking to simulate a delay
        first_backorder.scheduled_date = first_backorder.scheduled_date + timedelta(days=7)

        self.assertEqual(
            order.of_estimated_invoicing_date,
            copied_picking.scheduled_date.date(),
            "The estimated invoicing date should be equal to the date of the closest scheduled date of pickings linked "
            "to the sale order.",
        )

    def test_05_of_estimated_invoicing_date_without_fixed_date_all_done(self):
        """Test the estimated invoicing date without a fixed invoice date and all pickings are done.
        The estimated invoicing date should be equal to the date of the last done picking."""
        order = self.env['sale.order'].create(self._prepare_sale_order_values(dict(quantity=3)))
        order.of_invoice_policy = 'delivery'
        order.action_verification_confirm()
        self.assertEqual(len(order.picking_ids), 1, "The sale order should have one picking")

        # Confirm the delivery with a missing quantity to generate a backorder
        first_picking = order.picking_ids[0]
        first_picking.move_line_ids[0].qty_done = 1
        backorder_wizard_dict = first_picking.button_validate()
        backorder_wizard = Form(
            self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])
        ).save()
        backorder_wizard.process()
        self.assertEqual(len(order.picking_ids), 2, "The sale order should have two pickings")

        first_backorder = order.picking_ids.filtered(lambda p: p.backorder_id)

        # Easy way to simulate a second picking/backorder linked to the sale order to test the estimated invoicing date.
        # As we just want another picking without take care of the quantity, we can copy the first backorder.
        copied_picking = first_backorder.copy()

        # Update the scheduled date of the first picking to simulate a delay
        first_backorder.scheduled_date = first_backorder.scheduled_date + timedelta(days=7)

        # Process all pickings
        first_backorder.move_line_ids[0].qty_done = 1
        first_backorder.button_validate()

        # Add a product to the second picking to be able to validate it
        copied_picking.write(
            {'move_line_ids': [Command.create({'product_id': self.product_consu_a.id, 'qty_done': 1})]}
        )
        copied_picking.button_validate()

        self.assertEqual(
            order.of_estimated_invoicing_date,
            order.picking_ids[-1].scheduled_date.date(),
            "The estimated invoicing date should be equal to the date of the last done picking.",
        )
