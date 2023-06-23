# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def get_years():
    year_list = []
    for i in range(2020, 2031):
        year_list.append((i, str(i)))
    return year_list


class OFSaleObjective(models.Model):
    """Objectif mensuel de ventes"""

    _name = 'of.sale.objective'
    _description = "Monthly sales objective"
    _order = 'year desc, month desc'

    company_id = fields.Many2one(comodel_name='res.company', string="Shop", required=True)
    month = fields.Selection(
        selection=[
            ('01', "January"),
            ('02', "February"),
            ('03', "Mach"),
            ('04', "April"),
            ('05', "May"),
            ('06', "June"),
            ('07', "July"),
            ('08', "August"),
            ('09', "September"),
            ('10', "October"),
            ('11', "November"),
            ('12', "December"),
        ],
        required=True,
    )
    year = fields.Selection(selection=get_years(), required=True)
    objective_line_ids = fields.One2many(
        comodel_name='of.sale.objective.line', inverse_name='objective_id', string="Objective lines"
    )
    objective_date = fields.Date(string="Date", compute="_compute_objective_date", store=True)

    @api.depends('month', 'year')
    def _compute_objective_date(self):
        for objective in self:
            objective.objective_date = fields.Date.to_string(
                date(year=objective.year, month=int(objective.month), day=1)
            )

    @api.multi
    def name_get(self):
        res = []
        for obj in self:
            res.append((obj.id, '%s - %s %s' % (obj.company_id.name, obj.month, obj.year)))
        return res

    @api.model
    def create(self, vals):
        # On vérifie qu'un objectif mensuel n'existe pas déjà pour ce magasin et ce mois
        if self.search(
            [
                ('company_id', '=', vals.get('company_id')),
                ('month', '=', vals.get('month')),
                ('year', '=', vals.get('year')),
            ]
        ):
            raise UserError(_("A monthly objective has already be set for this shop and month"))

        res = super(OFSaleObjective, self).create(vals)

        # On crée les lignes d'objectif pour tous les vendeurs du magasin
        line_vals = [
            (0, 0, {'employee_id': employee.id})
            for employee in self.env['hr.employee'].search(
                [('company_id', '=', res.company_id.id), ('sale_objective', '=', True)]
            )
        ]
        res.objective_line_ids = line_vals

        return res


class OFSaleObjectiveLine(models.Model):
    """Ligne d'objectif mensuel de ventes"""

    _name = 'of.sale.objective.line'
    _description = "Monthly sales objective line"
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
            "A same employee can't have two objectives on the same month!",
        )
    ]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sale_objective = fields.Boolean(
        string="Sale objectives", help="Indique si des objectifs de ventes doivent être définis pour cet employé"
    )
