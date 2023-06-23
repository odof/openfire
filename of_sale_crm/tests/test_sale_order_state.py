# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestSaleOrderState(TestOFSaleCommon):
    def test_01_create_order_with_estimate_start_state(self):
        """Test the creation of a sale order with the start state set to 'estimate'.
        The state of the sale order should be 'draft'.
        """
        settings = self.env['res.config.settings'].create({})
        settings.of_sale_order_start_state = 'estimate'
        settings.execute()

        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        self.assertEqual(order.state, 'draft')

    def test_02_create_order_with_quotation_start_state(self):
        """Test the creation of a sale order with the start state set to 'quotation'.
        The state of the sale order should be 'sent'."""
        settings = self.env['res.config.settings'].create({})
        settings.of_sale_order_start_state = 'quotation'
        settings.execute()

        order = self.env['sale.order'].create(self._prepare_sale_order_values())
        self.assertEqual(order.state, 'sent')

    def test_03_create_order_with_quotation_start_state(self):
        """Test the creation of a sale order with the start state set to 'quotation' by forcing the state.
        The state of the sale order should be 'sent'."""
        settings = self.env['res.config.settings'].create({})
        settings.of_sale_order_start_state = 'quotation'
        settings.execute()

        order_values = self._prepare_sale_order_values()
        order_values['state'] = 'draft'
        order = self.env['sale.order'].create(order_values)

        self.assertEqual(order.state, 'sent')

    def test_04_sale_order_send_email_with_estimate_start_state(self):
        """Test the sending of a sale order by email with the start state set to 'estimate'.
        The state of the sale order should be 'draft' and the order should be marked as 'quotation sent'.
        """
        settings = self.env['res.config.settings'].create({})
        settings.of_sale_order_start_state = 'estimate'
        settings.execute()

        order = self.env['sale.order'].create(self._prepare_sale_order_values())

        order.action_quotation_send()
        email_act = order.action_quotation_send()
        email_ctx = email_act.get('context', {})
        order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))

        self.assertEqual(order.state, 'draft')
        self.assertTrue(order.of_sent_quotation)

    def test_05_sale_order_send_email_with_quotation_start_state(self):
        """Test the sending of a sale order by email with the start state set to 'quotation'.
        The state of the sale order should be 'sent' and the order should be marked as 'quotation sent'.
        """
        settings = self.env['res.config.settings'].create({})
        settings.of_sale_order_start_state = 'quotation'
        settings.execute()

        order = self.env['sale.order'].create(self._prepare_sale_order_values())

        self.assertEqual(order.state, 'sent')

        email_act = order.action_quotation_send()
        email_ctx = email_act.get('context', {})
        order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))

        self.assertEqual(order.state, 'sent')
        self.assertTrue(order.of_sent_quotation, "The order should be marked as 'quotation sent'")
