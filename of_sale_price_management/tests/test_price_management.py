# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo.fields import Command
from odoo.tests import Form
from odoo.tools import float_compare

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFPriceManagementWizard(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Product and sale data
        cls.of_product_1 = cls.create_product(
            {
                'name': 'of_product_test_1',
                'standard_price': 34.10,
                'list_price': 66.0,
                'default_code': 'BA_TEST_1',
            }
        )
        cls.of_product_2 = cls.create_product(
            {
                'name': 'of_product_test_2',
                'standard_price': 36.30,
                'list_price': 71.00,
                'default_code': 'BA_TEST_2',
            }
        )
        cls.product_discount = cls.create_product(
            {
                'name': 'of_product_discount',
                'standard_price': 0.0,
                'list_price': 0.0,
                'type': 'service',
            }
        )

    def _prepare_sale_order_values(self):
        return {
            'partner_id': self.customer_a.id,
            'partner_invoice_id': self.customer_a.id,
            'partner_shipping_id': self.customer_a.id,
            'pricelist_id': self.default_pricelist.id,
            'fiscal_position_id': self.fiscal_pos_5_5.id,
            'order_line': [
                Command.create(
                    {
                        'product_id': self.of_product_1.id,
                        'product_uom_qty': 1,
                        'price_unit': 150,  # force price unit to 150
                        'purchase_price': 45,  # force purchase price to 45
                        'tax_id': self.tax_base,
                    }
                ),
                Command.create(
                    {
                        'product_id': self.of_product_2.id,
                        'product_uom_qty': 1,
                        'price_unit': 90,  # force price unit to 90
                        'purchase_price': 50,  # force purchase price to 50
                        'tax_id': self.tax_base,
                    }
                ),
            ],
        }

    def _create_sale_order(self):
        return self.env['sale.order'].create(self._prepare_sale_order_values())

    def _create_wizard(self, sale_order=None):
        price_management_obj = self.env['of.sale.price.management.wizard']

        if sale_order is None:
            # Create the SO with two order lines
            sale_order = self._create_sale_order()

        ctx = self.env.context.copy()
        ctx.update(
            {
                'active_model': 'sale.order',
                'active_ids': [sale_order.id],
                'active_id': sale_order.id,
            }
        )
        line_vals = [Command.create(line._prepare_price_management_line_values()) for line in sale_order.order_line]
        return price_management_obj.with_context(ctx).create(
            {
                'order_id': sale_order.id,
                'line_ids': line_vals,
            }
        )

    def test_01_wizard_initialization_values(self):
        """Test the price management wizard. Test amounts and taxes are correctly initialized."""

        # Create the wizard
        price_management = self._create_wizard()

        # Check initial values
        self.assertEqual(len(price_management.line_ids), 2)
        self.assertRecordValues(
            price_management.line_ids,
            [
                {
                    'product_id': self.of_product_1.id,
                    'total_cost_tax_excl': 45.0,
                    'total_price_tax_excl': 150.0,
                    'total_price_tax_incl': 158.25,
                    'tax_ids': [self.tax_base.id],
                },
                {
                    'product_id': self.of_product_2.id,
                    'total_cost_tax_excl': 50.0,
                    'total_price_tax_excl': 90.0,
                    'total_price_tax_incl': 94.95,
                    'tax_ids': [self.tax_base.id],
                },
            ],
        )
        self.assertEqual(price_management.init_total_amount_tax_excl, 240.0)
        self.assertEqual(float_compare(price_management.init_total_amount_tax_incl, 253.20, precision_digits=2), 0)
        self.assertEqual(price_management.initial_margin, 145)
        self.assertEqual(float_compare(price_management.initial_margin_percent, 0.6042, precision_digits=4), 0)
        self.assertEqual(price_management.init_total_amount_tax_excl, price_management.total_amount_sim_tax_excl)
        self.assertEqual(price_management.init_total_amount_tax_incl, price_management.total_amount_sim_tax_incl)
        self.assertEqual(
            float_compare(price_management.initial_margin, price_management.simulated_margin, precision_digits=4), 0
        )
        self.assertEqual(
            float_compare(
                price_management.initial_margin_percent, price_management.simulated_margin_percent, precision_digits=4
            ),
            0,
        )

    def test_02_discount_type_margin_percent_not_available(self):
        """Test that the discount type 'Margin %' is not available for the current user if he is not in the group
        'OF Margin > Manager'.
        """
        price_management = self._create_wizard()

        selection_values = price_management._fields.get('discount_type').get_description(self.env).get('selection')
        self.assertNotIn('margin_percent', list(map(lambda x: x[0], selection_values)))

    def test_03_discount_type_margin_percent_available(self):
        """Test that the discount type 'Margin %' is available for the current user if he is in the group
        'OF Margin > Manager'.
        """
        self.env.user.write({'groups_id': [(4, self.env.ref('of_sale_margin.of_group_sale_margin_manager').id)]})

        price_management = self._create_wizard()

        selection_values = price_management._fields.get('discount_type').get_description(self.env).get('selection')
        self.assertIn('margin_percent', list(map(lambda x: x[0], selection_values)))

    def test_04_discount_type_total_target_amnt_tax_incl(self):
        """Test the discount type 'Total target amount incl. VAT'"""
        # Create the wizard
        price_management = self._create_wizard()

        # Total target amount incl. VAT
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'total_target_amnt_tax_incl'
            price_management_form.value = 250.0

        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 148.10,
                    'margin': 103.10,
                    'margin_percent': 69.62,
                    'sim_total_price_tax_incl': 156.25,
                },
                {
                    'sim_total_cost_tax_excl': 50,
                    'sim_total_price_tax_excl': 88.86,
                    'margin': 38.86,
                    'margin_percent': 43.73,
                    'sim_total_price_tax_incl': 93.75,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_05_discount_type_amount_tax_incl(self):
        """Test the discount type 'Amount incl. VAT'"""
        # Create the wizard
        price_management = self._create_wizard()

        # Amount incl. VAT to be deducted
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'amount_tax_incl'
            price_management_form.value = 75.0

        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 105.57,
                    'margin': 60.57,
                    'margin_percent': 57.37,
                    'sim_total_price_tax_incl': 111.38,
                },
                {
                    'sim_total_cost_tax_excl': 50,
                    'sim_total_price_tax_excl': 63.34,
                    'margin': 13.34,
                    'margin_percent': 21.06,
                    'sim_total_price_tax_incl': 66.82,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_06_discount_type_total_target_amnt_tax_excl(self):
        """Test the discount type 'Total target amount excl. VAT'"""
        # Create the wizard
        price_management = self._create_wizard()

        # Total target amount excl. VAT
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'total_target_amnt_tax_excl'
            price_management_form.value = 250.0

        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 156.25,
                    'margin': 111.25,
                    'margin_percent': 71.20,
                    'sim_total_price_tax_incl': 164.84,
                },
                {
                    'sim_total_cost_tax_excl': 50,
                    'sim_total_price_tax_excl': 93.75,
                    'margin': 43.75,
                    'margin_percent': 46.67,
                    'sim_total_price_tax_incl': 98.91,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_07_discount_type_amount_tax_excl(self):
        """Test the discount type 'Amount excl. VAT'"""
        # Create the wizard
        price_management = self._create_wizard()

        # Amount excl. VAT to be deducted
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'amount_tax_excl'
            price_management_form.value = 75.0

        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 103.13,
                    'margin': 58.13,
                    'margin_percent': 56.37,
                    'sim_total_price_tax_incl': 108.80,
                },
                {
                    'sim_total_cost_tax_excl': 50,
                    'sim_total_price_tax_excl': 61.87,
                    'margin': 11.87,
                    'margin_percent': 19.19,
                    'sim_total_price_tax_incl': 65.27,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_08_discount_type_percentage(self):
        """Test the discount type 'Percentage'"""
        # Create the wizard
        price_management = self._create_wizard()

        # % Overall discount
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'percentage'
            price_management_form.value = 15.0
        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 127.50,
                    'margin': 82.50,
                    'margin_percent': 64.71,
                    'sim_total_price_tax_incl': 134.51,
                },
                {
                    'sim_total_cost_tax_excl': 50,
                    'sim_total_price_tax_excl': 76.50,
                    'margin': 26.50,
                    'margin_percent': 34.64,
                    'sim_total_price_tax_incl': 80.71,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_09_discount_type_margin_percent(self):
        """Test the discount type 'Margin %'"""
        # Set user in group 'OF Margin > Manager'
        self.env.user.write({'groups_id': [(4, self.env.ref('of_sale_margin.of_group_sale_margin_manager').id)]})

        # Create the wizard
        price_management = self._create_wizard()

        # % Margin
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'margin_percent'
            price_management_form.value = 50.0

        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 118.75,
                    'margin': 73.75,
                    'margin_percent': 62.11,
                    'sim_total_price_tax_incl': 125.28,
                },
                {
                    'sim_total_cost_tax_excl': 50,
                    'sim_total_price_tax_excl': 71.25,
                    'margin': 21.25,
                    'margin_percent': 29.82,
                    'sim_total_price_tax_incl': 75.17,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_10_discount_type_restore(self):
        """Test the discount type 'Restore'"""
        # Create the wizard
        price_management = self._create_wizard()

        # Restore at store price
        with Form(price_management) as price_management_form:
            price_management_form.value = 0.0
            price_management_form.discount_type = 'restore'

        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 34.10,
                    'sim_total_price_tax_excl': 66.0,
                    'margin': 31.90,
                    'margin_percent': 48.33,
                    'sim_total_price_tax_incl': 69.63,
                },
                {
                    'sim_total_cost_tax_excl': 36.30,
                    'sim_total_price_tax_excl': 71.0,
                    'margin': 34.70,
                    'margin_percent': 48.87,
                    'sim_total_price_tax_incl': 74.91,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_10_discount_mode_totals_amount_tax_incl(self):
        """Test the discount mode 'Totals' with discount type 'Amount incl. VAT to be deducted'.
        The other mode 'Lines' is the default value and is tested through previous tests.
        """
        # Create the wizard
        price_management = self._create_wizard()

        # Apply price management on totals
        with Form(price_management) as price_management_form:
            price_management_form.discount_mode = 'total'
            price_management_form.discount_product_id = self.product_discount
            price_management_form.discount_type = 'amount_tax_incl'
            price_management_form.value = 50.0

        # Simulate
        price_management.action_button_simulate()

        # We should have 3 lines (2 products + 1 discount)
        self.assertEqual(len(price_management.line_ids), 3)

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 150.0,
                    'margin': 105.0,
                    'margin_percent': 70.0,
                    'sim_total_price_tax_incl': 158.25,
                },
                {
                    'sim_total_cost_tax_excl': 50.0,
                    'sim_total_price_tax_excl': 90.0,
                    'margin': 40.0,
                    'margin_percent': 44.44,
                    'sim_total_price_tax_incl': 94.95,
                },
                {
                    'sim_total_cost_tax_excl': 0,
                    'sim_total_price_tax_excl': -47.39,
                    'margin': -47.39,
                    'margin_percent': 100.0,
                    'sim_total_price_tax_incl': -50.0,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_11_discount_mode_totals_percentage(self):
        """Test the discount mode 'Totals' with discount type 'Percentage'.
        We just test at least one other discount type for this mode.
        """
        # Create the wizard
        price_management = self._create_wizard()

        # Apply price management on totals
        with Form(price_management) as price_management_form:
            price_management_form.discount_mode = 'total'
            price_management_form.discount_product_id = self.product_discount
            price_management_form.discount_type = 'percentage'
            price_management_form.value = 15.0

        # Simulate
        price_management.action_button_simulate()

        # We should have 3 lines (2 products + 1 discount)
        self.assertEqual(len(price_management.line_ids), 3)

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 150.0,
                    'margin': 105.0,
                    'margin_percent': 70.0,
                    'sim_total_price_tax_incl': 158.25,
                },
                {
                    'sim_total_cost_tax_excl': 50.0,
                    'sim_total_price_tax_excl': 90.0,
                    'margin': 40.0,
                    'margin_percent': 44.44,
                    'sim_total_price_tax_incl': 94.95,
                },
                {
                    'sim_total_cost_tax_excl': 0,
                    'sim_total_price_tax_excl': -36.0,
                    'margin': -36.0,
                    'margin_percent': 100.0,
                    'sim_total_price_tax_incl': -37.98,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_12_rounding_mode_total_excluded(self):
        """Test the rounding mode 'Total Excluded'"""
        # Create the wizard
        price_management = self._create_wizard()

        # Rounding mode total excluded with precision "Round up to the nearest €10"
        with Form(price_management) as price_management_form:
            self._edit_form_rounding_mode(price_management_form, 'percentage', 15.0, 'total_excluded', '-1')
        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 130.0,
                    'margin': 85.0,
                    'margin_percent': 65.38,
                    'sim_total_price_tax_incl': 137.15,
                },
                {
                    'sim_total_cost_tax_excl': 50.0,
                    'sim_total_price_tax_excl': 70.0,
                    'margin': 20,
                    'margin_percent': 28.57,
                    'sim_total_price_tax_incl': 73.85,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

        # Rounding mode total excluded with precision "Round to the nearest 10 cents"
        with Form(price_management) as price_management_form:
            self._edit_form_rounding_mode(price_management_form, 'percentage', 15.0, 'total_excluded', '1')
        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 127.50,
                    'margin': 82.50,
                    'margin_percent': 64.71,
                    'sim_total_price_tax_incl': 134.51,
                },
                {
                    'sim_total_cost_tax_excl': 50.0,
                    'sim_total_price_tax_excl': 76.50,
                    'margin': 26.50,
                    'margin_percent': 34.64,
                    'sim_total_price_tax_incl': 80.71,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_13_rounding_mode_total_included(self):
        """Test the rounding mode 'Total Included'"""
        # Create the wizard
        price_management = self._create_wizard()

        # Rounding mode total excluded with precision "Round up to the nearest €10"
        with Form(price_management) as price_management_form:
            self._edit_form_rounding_mode(price_management_form, 'percentage', 15.0, 'total_included', '-1')
        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 123.23,  # FIXME: should be 123.22 ?
                    'margin': 78.23,  # FIXME: should be 78.22 ?
                    'margin_percent': 63.48,
                    'sim_total_price_tax_incl': 130.01,  # FIXME: should be 130.0 ?
                },
                {
                    'sim_total_cost_tax_excl': 50.0,
                    'sim_total_price_tax_excl': 85.31,
                    'margin': 35.31,
                    'margin_percent': 41.39,
                    'sim_total_price_tax_incl': 90.0,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

        # Rounding mode total excluded with precision "Round to the nearest 10 cents"
        with Form(price_management) as price_management_form:
            self._edit_form_rounding_mode(price_management_form, 'percentage', 15.0, 'total_included', '1')
        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 127.49,
                    'margin': 82.49,
                    'margin_percent': 64.70,
                    'sim_total_price_tax_incl': 134.50,
                },
                {
                    'sim_total_cost_tax_excl': 50.0,
                    'sim_total_price_tax_excl': 76.49,
                    'margin': 26.49,
                    'margin_percent': 34.63,
                    'sim_total_price_tax_incl': 80.70,
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_14_calculation_basis_on_cost(self):
        """Test calculation basis on cost. All previous tests are done with calculation basis on sale price.
        So we take the same test as `test_04_discount_type_total_target_amnt_tax_incl` and we change the
        calculation basis to cost.
        """

        # Create the wizard
        price_management = self._create_wizard()

        # Total target amount incl. VAT
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'total_target_amnt_tax_incl'
            price_management_form.value = 250.0
            price_management_form.calculation_basis = 'cost'

        # Simulate
        price_management.action_button_simulate()

        # Check lines values
        for index, expected_values in enumerate(
            [
                {
                    'sim_total_cost_tax_excl': 45.0,
                    'sim_total_price_tax_excl': 112.24,  # FIXME: should be 112.25 ?
                    'margin': 67.24,  # FIXME: should be 67.25 ?
                    'margin_percent': 59.91,
                    'sim_total_price_tax_incl': 118.41,  # FIXME: should be 118.42 ?
                },
                {
                    'sim_total_cost_tax_excl': 50,
                    'sim_total_price_tax_excl': 124.73,  # FIXME: should be 124.72 ?
                    'margin': 74.73,  # FIXME: should be 74.72 ?
                    'margin_percent': 59.91,
                    'sim_total_price_tax_incl': 131.59,  # FIXME: should be 131.58 ?
                },
            ]
        ):
            self._assert_values_price_management(price_management, index, expected_values)

    def test_15_wizard_action_bouton_validate(self):
        """Test the wizard action bouton validate"""
        # Create the wizard
        price_management = self._create_wizard()

        # Total target amount incl. VAT
        with Form(price_management) as price_management_form:
            price_management_form.discount_type = 'total_target_amnt_tax_incl'
            price_management_form.value = 250.0
            price_management_form.display_discount = True

        # Simulate
        price_management.action_button_simulate()

        # Confirm
        price_management.action_bouton_validate()

        order = price_management.order_id
        # Check lines values
        self.assertEqual(
            float_compare(
                order.order_line[0].price_unit,
                148.10,
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                order.order_line[1].price_unit,
                88.86,
                precision_digits=2,
            ),
            0,
        )
        # Check order totals
        self.assertEqual(
            float_compare(
                order.amount_untaxed,
                236.96,
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                order.amount_tax,
                13.04,
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                order.amount_total,
                250.0,
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                order.margin,
                141.96,
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                order.margin_percent * 100.0,
                59.91,
                precision_digits=2,
            ),
            0,
        )
        # Check order note
        self.assertEqual(order.note, Markup('<p>Remise exceptionnelle déduite de 3,20&nbsp;€.\n</p>'))

    def _edit_form_rounding_mode(self, price_management_form, discount_type, value, rounding_mode, rounding_precision):
        """Helper function to edit the form with the given rounding mode and precision."""
        price_management_form.discount_type = discount_type
        price_management_form.value = value
        price_management_form.rounding_mode = rounding_mode
        price_management_form.rounding_precision = rounding_precision

    def _assert_values_price_management(self, price_management, index, expected_values):
        """Helper function to assert the values of the price management line at the given index when simulating."""
        self.assertEqual(
            float_compare(
                price_management.line_ids[index].sim_total_cost_tax_excl,
                expected_values['sim_total_cost_tax_excl'],
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                price_management.line_ids[index].sim_total_price_tax_excl,
                expected_values['sim_total_price_tax_excl'],
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                price_management.line_ids[index].margin,
                expected_values['margin'],
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                price_management.line_ids[index].margin_percent,
                expected_values['margin_percent'],
                precision_digits=2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                price_management.line_ids[index].sim_total_price_tax_incl,
                expected_values['sim_total_price_tax_incl'],
                precision_digits=2,
            ),
            0,
        )
