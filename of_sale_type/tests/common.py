# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale_management_template.tests.common import TestOFSaleManagementCommon


class TestOFSaleOrderTypeCommon(TestOFSaleManagementCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.default_sale_order_type = cls.env['sale.order.type'].create(
            {
                'name': "Defaut Type 1",
            }
        )

    def _prepare_sale_order_values(self, default_values=None):
        if default_values is None:
            default_values = {}
        order_values = super()._prepare_sale_order_values(default_values)
        order_values['type_id'] = default_values.get('type_id', self.default_sale_order_type.id)
        return order_values
