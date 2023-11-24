# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleOrderOpportunityCopy(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    def test_01_sale_order_copy_data_ok(self):
        """
        This test checks that the opportunity is correctly copied when the sale order is copied.
        """
        # Change the value of the parameter
        self.env['res.config.settings'].create(
            {
                'of_copy_opportunity_with_sale_order': True,
            }
        ).execute()

        # Create a sale order with an opportunity
        order_values = self._prepare_empty_sale_order_values()
        order_values['opportunity_id'] = self.env['crm.lead'].create({'name': 'Test Opportunity'}).id
        sale_order = self.env['sale.order'].create(order_values)

        # Copy the sale order
        copied_sale_order = sale_order.copy()

        # Check that the opportunity is copied
        self.assertEqual(
            copied_sale_order.opportunity_id.id,
            sale_order.opportunity_id.id,
            "The opportunity should be copied when the sale order is copied.",
        )

    def test_02_sale_order_copy_data_ko(self):
        """
        This test checks that the opportunity is not copied when the sale order is copied.
        """
        # Change the value of the parameter
        self.env['res.config.settings'].create(
            {
                'of_copy_opportunity_with_sale_order': False,
            }
        ).execute()
        # Create a sale order without an opportunity
        order_values = self._prepare_empty_sale_order_values()
        order_values['opportunity_id'] = self.env['crm.lead'].create({'name': 'Test Opportunity'}).id
        sale_order = self.env['sale.order'].create(order_values)

        # Copy the sale order
        copied_sale_order = sale_order.copy()

        # Check that the opportunity is not copied
        self.assertFalse(
            copied_sale_order.opportunity_id,
            "The opportunity should not be copied when the sale order is copied.",
        )
