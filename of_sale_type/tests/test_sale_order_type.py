# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_sale_management_template.tests.common import TestOFSaleManagementCommon


class TestSaleOrderType(TestOFSaleManagementCommon):
    def setUp(self):
        super().setUp()
        self.sale_order_type = self.env['sale.order.type'].create(
            {
                'name': 'Type de devis',
            }
        )
        self.sale_order_template_1.of_order_type_id = self.sale_order_type.id

    def test_01_onchange_sale_order_template_id(self):
        """Test onchange sale_order_template_id. The sale_order_template has an order type.
        Sale Order should have the same order type."""
        with Form(self.env['sale.order']) as order_form:
            order_form.partner_id = self.customer_a
            order_form.sale_order_template_id = self.sale_order_template_1
            sale_order = order_form.save()

        # Vérification des champs copiés
        self.assertEqual(sale_order.type_id, self.sale_order_type)
