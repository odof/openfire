# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import fields

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


@freeze_time("2025-01-07 07:00:00")
class TestOFSaleOrderLayingDate(TestOFSaleCommon):
    def setUp(self):
        super().setUp()
        self.sale_order = self.env["sale.order"].create(self._prepare_sale_order_values())

    def test_01_sale_order_laying_date_compute(self):
        """Test computation of reference laying date and laying week for a sale order when we are forcing the date."""
        # Set manual laying date without forcing it
        self.sale_order.of_force_laying_date = False
        self.sale_order.of_manual_laying_date = fields.Date.today()
        self.sale_order._compute_of_reference_laying_data()

        # Without force, reference date should be False
        self.assertFalse(self.sale_order.of_reference_laying_date)
        self.assertEqual(self.sale_order.of_laying_week, "Non programmée")

        # Enable force laying date
        self.sale_order.of_force_laying_date = True
        self.sale_order._compute_of_reference_laying_data()

        # With force enabled, should use manual date
        self.assertEqual(self.sale_order.of_reference_laying_date, fields.Date.from_string("2025-01-07"))
        self.assertEqual(self.sale_order.of_laying_week, "2025 - S02")

        # Test with different date
        self.sale_order.of_manual_laying_date = fields.Date.today().replace(year=2025, month=2, day=1)
        self.sale_order._compute_of_reference_laying_data()
        self.assertEqual(self.sale_order.of_reference_laying_date, fields.Date.from_string("2025-02-01"))
        self.assertEqual(self.sale_order.of_laying_week, "2025 - S05")

        # Disable force laying date
        self.sale_order.of_force_laying_date = False
        self.sale_order._compute_of_reference_laying_data()
        self.assertFalse(self.sale_order.of_reference_laying_date)
        self.assertEqual(self.sale_order.of_laying_week, "Non programmée")
