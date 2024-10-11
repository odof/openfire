# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestSaleOrderStateConfirmEstimate(TestOFSaleCommon):
    def test_01_action_button_confirm_estimate(self):
        """
        This test checks that the state of the sale order is changed to 'sent'
        when the action_button_confirm_estimate method is called.
        """
        self.env["ir.config_parameter"].sudo().set_param("of.sale.crm.sale.order.start_state", "estimate")

        sale_order = self.env["sale.order"].create(self._prepare_sale_order_values())
        sale_order.action_button_confirm_estimate()
        self.assertEqual(sale_order.state, "sent", "The state of the sale order should be changed to 'sent'")
