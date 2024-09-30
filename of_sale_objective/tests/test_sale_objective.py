# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError

from odoo.addons.of_sale.tests.common import TestOFSaleCommon

from ..models.of_sale_objective import DEFAULT_YEARS_RANGE


class TestOFSaleObjective(TestOFSaleCommon):
    def test_01_create_sale_objective(self):
        """Test the creation of a sale objective for Employees with sale_objective field set to True"""
        # Create some employees
        self.employee_01 = self.env["hr.employee"].create(
            {
                "name": "Employee 01",
                "sale_objective": True,
                "company_id": self.company_fr.id,
            }
        )
        self.employee_02 = self.env["hr.employee"].create(
            {
                "name": "Employee 01",
                "sale_objective": True,
                "company_id": self.company_fr.id,
            }
        )
        self.employee_03 = self.env["hr.employee"].create(
            {
                "name": "Employee 01",
                "sale_objective": False,
                "company_id": self.company_fr.id,
            }
        )

        # Create a sale objective
        sale_objective_id = self.env["of.sale.objective"].create(
            {
                "month": "02",
                "year": "2024",
                "company_id": self.company_fr.id,
            }
        )
        self.assertEqual(len(sale_objective_id.objective_line_ids), 2)
        self.assertIsNotNone(sale_objective_id)

    def test_02_sale_objective_record_is_duplicated(self):
        """Test that a sale objective record cannot be duplicated for the same month and year"""
        self.env["of.sale.objective"].create(
            {
                "month": "02",
                "year": "2024",
                "company_id": self.company_fr.id,
            }
        )
        with self.assertRaises(UserError):
            self.env["of.sale.objective"].create(
                {
                    "month": "02",
                    "year": "2024",
                    "company_id": self.company_fr.id,
                }
            )

    def test_03_get_default_years_range(self):
        """Test the default range of years with config parameter, we shouldn't be able to create a sale objective
        for a year outside the range"""
        # we change the year range
        range_parameter = self.env["ir.config_parameter"].sudo().search([("key", "=", "of_sale_objective.years_range")])
        range_parameter.write({"value": "2024;2027"})
        with self.assertRaises(ValueError):
            self.env["of.sale.objective"].create(
                {
                    "month": "02",
                    "year": "2020",
                    "company_id": self.company_fr.id,
                }
            )
        with self.assertRaises(ValueError):
            self.env["of.sale.objective"].create(
                {
                    "month": "02",
                    "year": "2031",
                    "company_id": self.company_fr.id,
                }
            )
        sale_obj_id = self.env["of.sale.objective"].create(
            {
                "month": "04",
                "year": "2024",
                "company_id": self.company_fr.id,
            }
        )
        self.assertIsNotNone(sale_obj_id)

    def test_04_get_default_years_range_default_range_without_parameter(self):
        """Test the default range of years without config parameter, we shouldn't be able to create a sale objective
        for a year outside the range"""

        # we are deleting the config parameter
        range_parameter = self.env["ir.config_parameter"].sudo().search([("key", "=", "of_sale_objective.years_range")])
        range_parameter.unlink()

        # we check that the default range is the same as the one in the code
        range_start, range_stop = DEFAULT_YEARS_RANGE.split(";")
        range_start = int(range_start)
        range_stop = int(range_stop)

        # we check that we can't create a sale objective for a year outside the range
        with self.assertRaises(ValueError):
            self.env["of.sale.objective"].create(
                {
                    "month": "02",
                    "year": str(range_start - 1),
                    "company_id": self.company_fr.id,
                }
            )
        with self.assertRaises(ValueError):
            self.env["of.sale.objective"].create(
                {
                    "month": "02",
                    "year": str(range_stop + 1),
                    "company_id": self.company_fr.id,
                }
            )

        # we check that we can create a sale objective for a year inside the range
        sale_obj_id = self.env["of.sale.objective"].create(
            {
                "month": "04",
                "year": str(range_start + 1),
                "company_id": self.company_fr.id,
            }
        )
        self.assertIsNotNone(sale_obj_id)
