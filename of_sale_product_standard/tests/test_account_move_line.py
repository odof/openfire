# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_sale_product_standard.tests.common import TestOFProductStandardCommon


class TestOFProductStandardMoveLineName(TestOFProductStandardCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set the standard on the product
        cls.product_standard_test.of_standard_id = cls.product_standard.id

    def test_01_account_move_line_compute_name(self):
        """Test that the name of the account move line is correctly computed when the product has a standard"""
        with Form(
            self.env["account.move"].with_context(
                default_move_type="out_invoice", default_journal_id=self.journal_sale.id
            )
        ) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_standard_test
                line_form.quantity = 1
                line_form.price_unit = 100
            move = move_form.save()
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertEqual(
            move.invoice_line_ids[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )

        # Change the standard of the product before adding a new line
        self.product_standard_test.of_standard_id = self.product_standard2.id

        with Form(move) as move_form:
            # Add a new line
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_standard_test
                line_form.quantity = 1
                line_form.price_unit = 100

        # Check that the name of the lines is correctly computed
        # The first line should not have changed
        # The second line should have the new standard
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertEqual(
            move.invoice_line_ids[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )
        self.assertEqual(
            move.invoice_line_ids[1].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S2 : This is the standard 2",
        )

        # Remove the standard of the product before adding a new line
        self.product_standard_test.of_standard_id = False

        with Form(move) as move_form:
            # Add a new line
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_standard_test
                line_form.quantity = 1
                line_form.price_unit = 100

        # Check that the name of the lines is correctly computed
        # The first two lines should not have changed
        self.assertEqual(len(move.invoice_line_ids), 3)
        self.assertEqual(
            move.invoice_line_ids[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )
        self.assertEqual(
            move.invoice_line_ids[1].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S2 : This is the standard 2",
        )
        self.assertEqual(
            move.invoice_line_ids[2].name,
            "[BC_PST_123] Product Standard Test",
        )
