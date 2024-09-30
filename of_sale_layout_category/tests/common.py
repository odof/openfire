# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleLayoutCategoryCommon(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def _prepare_sale_order_values(self, default_values=None):
        values = super()._prepare_sale_order_values(default_values)

        product_a = default_values.get("product", self.product_consu_a)
        product_b = self.product_consu_b
        price_unit = default_values.get("price_unit", 50)
        quantity = default_values.get("quantity", 1)
        values["order_line"] = [
            Command.create(
                {
                    "display_type": "line_section",
                    "of_section_name": "1",
                    "name": "Section 1",
                    "of_node_id": 1,
                    "of_parent_node_id": 0,
                    "of_level": 1,
                    "of_position_node": 0,
                    "of_show": True,
                }
            ),
            Command.create(
                {
                    "display_type": False,
                    "product_id": product_a.id,
                    "product_uom_qty": quantity,
                    "tax_id": self.tax_base,
                    "price_unit": price_unit,
                    "of_node_id": 2,
                    "of_parent_node_id": 1,
                    "of_level": 2,
                    "of_position_node": 1,
                }
            ),
            Command.create(
                {
                    "display_type": False,
                    "product_id": product_b.id,
                    "product_uom_qty": 2,
                    "tax_id": self.tax_base,
                    "price_unit": product_b.standard_price,
                    "of_node_id": 1,
                    "of_parent_node_id": 1,
                    "of_level": 2,
                    "of_position_node": 2,
                }
            ),
        ]
        return values
