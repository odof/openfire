# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestResConfigSettings(TestOFSaleCommon):
    def test_01_of_sale_order_start_state(self):
        """Test the computation of sale order start state"""
        settings = self.env['res.config.settings'].create({})
        settings.of_sale_order_start_state = 'estimate'
        settings._compute_sale_order_start_state()
        self.assertTrue(settings.group_of_estimate_sale_order_state)
        self.assertFalse(settings.group_of_quotation_sale_order_state)

        settings.of_sale_order_start_state = 'quotation'
        settings._compute_sale_order_start_state()
        self.assertFalse(settings.group_of_estimate_sale_order_state)
        self.assertTrue(settings.group_of_quotation_sale_order_state)

    def test_02_user_group_assignation_on_sale_order_start_state(self):
        """Test the assignation of user groups on sale order start state change"""

        settings = self.env['res.config.settings'].create({})
        settings.of_sale_order_start_state = 'estimate'
        settings.execute()
        self.assertTrue(self.user_salesman.has_group('of_sale_crm.group_of_estimate_sale_order_state'))
        self.assertFalse(self.user_salesman.has_group('of_sale_crm.group_of_quotation_sale_order_state'))
        self.assertTrue(self.user_sale_responsible.has_group('of_sale_crm.group_of_estimate_sale_order_state'))
        self.assertFalse(self.user_sale_responsible.has_group('of_sale_crm.group_of_quotation_sale_order_state'))
        self.assertTrue(self.user_sale_manager.has_group('of_sale_crm.group_of_estimate_sale_order_state'))
        self.assertFalse(self.user_sale_manager.has_group('of_sale_crm.group_of_quotation_sale_order_state'))

        settings.of_sale_order_start_state = 'quotation'
        settings.execute()
        self.assertFalse(self.user_salesman.has_group('of_sale_crm.group_of_estimate_sale_order_state'))
        self.assertTrue(self.user_salesman.has_group('of_sale_crm.group_of_quotation_sale_order_state'))
        self.assertFalse(self.user_sale_responsible.has_group('of_sale_crm.group_of_estimate_sale_order_state'))
        self.assertTrue(self.user_sale_responsible.has_group('of_sale_crm.group_of_quotation_sale_order_state'))
        self.assertFalse(self.user_sale_manager.has_group('of_sale_crm.group_of_estimate_sale_order_state'))
        self.assertTrue(self.user_sale_manager.has_group('of_sale_crm.group_of_quotation_sale_order_state'))
