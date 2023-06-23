# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleObjectiveLine(models.Model):
    """Monthly sales objective line"""

    _name = 'of.sale.objective.line'
    _description = __doc__
    _order = 'employee_id'

    objective_id = fields.Many2one(
        comodel_name='of.sale.objective', string="Linked monthly objective", required=True, ondelete='cascade'
    )
    employee_id = fields.Many2one(comodel_name='hr.employee', string="Vendor", required=True)
    turnover_budget = fields.Float()
    ordered_turnover = fields.Float()
    invoiced_turnover = fields.Float()
    company_id = fields.Many2one(related='objective_id.company_id', string="Company")
    objective_date = fields.Date(related='objective_id.objective_date', string="Date")

    _sql_constraints = [
        (
            'of_sale_objective_line_employee_uniq',
            'unique (objective_id, employee_id)',
            "A same employee can't have two objectives on the same month.",
        )
    ]
