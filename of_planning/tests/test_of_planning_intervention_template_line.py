# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestPlanningInterventionTemplateLine(TestOFPlanningCommon):
    def setUp(self):
        super().setUp()
        self.template_line = self.template_installation.line_ids[0]

    def test_01_onchange_product(self):
        """Test that changing the product resets the line data."""
        self.assertEqual(self.template_line.qty, 1)
        self.assertEqual(self.template_line.price_unit, 125.0)

        # Change line data
        self.template_line.qty = 2
        self.template_line.price_unit = 2000.0
        self.template_line.name = "Test description"
        self.template_line.product_id = False
        self.template_line.product_id = self.product_wood_stove

        # Check that line data has been reset
        self.assertEqual(self.template_line.qty, 1)
        self.assertEqual(self.template_line.price_unit, self.product_wood_stove.lst_price)
        self.assertEqual(
            self.template_line.name,
            f"{self.product_wood_stove.name}\n{self.product_wood_stove.description_sale or ''}",
        )

    def test_02_onchange_product_no_product(self):
        """Test that changing the product resets the line data."""
        self.template_line.product_id = False

        self.assertEqual(self.template_line.qty, 1)
        self.assertEqual(self.template_line.price_unit, 0.0)
        self.assertEqual(self.template_line.name, "")
