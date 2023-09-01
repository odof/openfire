# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import Form

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleOrderAddQuote(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

        self.order_to_update = self.env['sale.order'].create(self._prepare_sale_order_values())

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_add_quote_to_sale_order_non_validated(self):
        """Test that the quote is added to the sale order."""

        with self.assertRaises(UserError):
            # We can't add a quote to a non-validated sale order
            self.order_to_update.action_button_add_quote()

    def test_02_add_quote_to_sale_order_different_customer(self):
        """Test that a quote can't be added to a sale order if the customer is different"""

        # Confirm the sale order
        self.order_to_update.action_verification_confirm()

        # Create a new quote with a different customer
        new_customer = self.env['res.partner'].create(
            {
                'name': 'New Customer',
            }
        )
        quote_values = self._prepare_sale_order_values()
        quote_values['partner_id'] = new_customer.id
        quote_values['partner_invoice_id'] = new_customer.id
        quote_values['partner_shipping_id'] = new_customer.id
        self.env['sale.order'].create(quote_values)

        # Try to add the quote to the sale order
        wizard_action = self.order_to_update.action_button_add_quote()
        with self.assertRaises(AssertionError):
            with Form(self.env[wizard_action['res_model']].browse(wizard_action['res_id'])) as wizard_form:
                self.assertEqual(
                    len(wizard_form.addable_quote_ids),
                    0,
                    "The quote should not be addable because the customer is different",
                )
            # Assertion error is raised here because the wizard is closed without setting the quote_id (required field)

    def test_03_add_quote_to_sale_order_same_customer(self):
        """Test that a quote can be added to a sale order if the customer is the same"""
        # Confirm the sale order
        self.order_to_update.action_verification_confirm()

        # Create a new quote with same customer but a different product
        new_product = self.create_product(
            {
                'name': 'New Product',
                'default_code': 'BA_NP',
                'standard_price': 45,
                'list_price': 100,
            }
        )
        quote_values = self._prepare_sale_order_values(product=new_product)
        quote = self.env['sale.order'].create(quote_values)

        # Try to add the quote to the sale order
        wizard_action = self.order_to_update.action_button_add_quote()
        with Form(
            self.env[wizard_action['res_model']].browse(wizard_action['res_id']),
            view='of_sale.of_sale_order_add_quote_wizard_form_view',
        ) as wizard_form:
            self.assertEqual(len(wizard_form.addable_quote_ids), 1, "The quote should be addable to the sale order")

            wizard_form.quote_id = quote
            wizard = wizard_form.save()
        wizard.action_button_add_quote()

        self.assertEqual(len(self.order_to_update.order_line), 2, "The sale order should have 2 order lines")
        self.assertEqual(self.order_to_update.order_line[0].product_id, self.product_consu_a)
        self.assertEqual(self.order_to_update.order_line[1].product_id, new_product)
        self.assertEqual(quote.state, 'cancel', "The quote should be cancelled")
