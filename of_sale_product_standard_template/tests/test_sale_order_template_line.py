# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_sale_product_standard.tests.common import TestOFProductStandardCommon


class TestOFSaleOrderTemplateLineName(TestOFProductStandardCommon):
    def setUp(self):
        super().setUp()

    def test_01_sale_order_template_line_compute_name(self):
        """Test that the name of the sale order template line is correctly computed when the product has a standard"""
        template = self.env["sale.order.template"].create(
            {
                "name": "Sale Order Template",
                "sale_order_template_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_standard_test.id,
                            "product_uom_qty": 1,
                        }
                    )
                ],
            }
        )
        self.assertEqual(len(template.sale_order_template_line_ids), 1)
        self.assertEqual(
            template.sale_order_template_line_ids[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )

        # Change the standard of the product before adding a new line
        self.product_standard_test.of_standard_id = self.product_standard2.id
        template.write(
            {
                "sale_order_template_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_standard_test.id,
                            "product_uom_qty": 1,
                        }
                    )
                ]
            }
        )

        # Check that the name of the lines is correctly computed
        # The first line should not have changed
        # The second line should have the new standard
        self.assertEqual(len(template.sale_order_template_line_ids), 2)
        self.assertEqual(
            template.sale_order_template_line_ids[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )
        self.assertEqual(
            template.sale_order_template_line_ids[1].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S2 : This is the standard 2",
        )

        # Remove the standard of the product before adding a new line
        self.product_standard_test.of_standard_id = False

        # Add a new line
        template.write(
            {
                "sale_order_template_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_standard_test.id,
                            "product_uom_qty": 1,
                        }
                    )
                ]
            }
        )

        # Check that the name of the lines is correctly computed
        # The first two lines should not have changed but the third line should not have the standard
        self.assertEqual(len(template.sale_order_template_line_ids), 3)
        self.assertEqual(
            template.sale_order_template_line_ids[0].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S1 : This is the standard 1",
        )
        self.assertEqual(
            template.sale_order_template_line_ids[1].name,
            "[BC_PST_123] Product Standard Test\nConforme à la norme S2 : This is the standard 2",
        )
        self.assertEqual(
            template.sale_order_template_line_ids[2].name,
            "[BC_PST_123] Product Standard Test",
        )
