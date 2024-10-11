# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DEFAULT_YEARS_RANGE = "2020;2031"


class OFSaleObjective(models.Model):
    """Monthly sales objective"""

    _name = "of.sale.objective"
    _description = __doc__
    _order = "year desc, month desc"

    @api.model
    def _get_default_years_range(self):
        range_str = (
            self.env["ir.config_parameter"].sudo().get_param("of_sale_objective.years_range", DEFAULT_YEARS_RANGE)
        )
        if (
            ";" not in range_str
            or len(range_str.split(";")) != 2
            or not range_str.split(";")[0].isdigit()
            or not range_str.split(";")[1].isdigit()
        ):
            range_str = DEFAULT_YEARS_RANGE
        range_start, range_stop = range_str.split(";")
        return [(str(i), str(i)) for i in range(int(range_start), int(range_stop) + 1)]

    company_id = fields.Many2one(comodel_name="res.company", string="Shop", required=True)
    month = fields.Selection(
        selection=[
            ("01", "January"),
            ("02", "February"),
            ("03", "March"),
            ("04", "April"),
            ("05", "May"),
            ("06", "June"),
            ("07", "July"),
            ("08", "August"),
            ("09", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        required=True,
    )
    year = fields.Selection(selection=lambda self: self._get_default_years_range(), required=True)
    objective_line_ids = fields.One2many(
        comodel_name="of.sale.objective.line", inverse_name="objective_id", string="Objective lines"
    )
    objective_date = fields.Date(string="Date")

    def name_get(self):
        return [(obj.id, f"{obj.company_id.name} - {obj.month} {obj.year}") for obj in self]

    def _check_create(self, vals):
        # We check that a monthly objective does not already exist for this store and this month
        if self.search(
            [
                ("company_id", "=", vals.get("company_id")),
                ("month", "=", vals.get("month")),
                ("year", "=", vals.get("year")),
            ]
        ):
            raise UserError(_("A monthly goal has already been set for this store and this month!"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_create(vals)
        records = super().create(vals_list)
        self._populate_objective_lines(records)
        return records

    def _populate_objective_lines(self, records):
        companies = records.mapped("company_id")
        employees = self.env["hr.employee"].search([("company_id", "in", companies.ids), ("sale_objective", "=", True)])
        for employee in employees:
            for record in records:
                if record.company_id == employee.company_id:
                    employee_value = {"employee_id": employee.id, "objective_id": record.id}
                    self.env["of.sale.objective.line"].create(employee_value)
        return records
