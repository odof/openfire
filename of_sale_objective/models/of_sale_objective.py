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

    @api.model_create_multi
    def create(self, vals_list):
        # On vérifie qu'un objectif mensuel n'existe pas déjà pour ce magasin et ce mois
        for vals in vals_list:
            # todo: remplacer par une contrainte SQL ?
            if self.search(
                [
                    ('company_id', '=', vals.get('company_id')),
                    ('month', '=', vals.get('month')),
                    ('year', '=', vals.get('year')),
                ]
            ):
                raise UserError(_("A monthly objective has already be set for this shop and month"))

        res = super().create(vals_list)

        for record in res:
            # On crée les lignes d'objectif pour tous les vendeurs du magasin
            line_vals = [
                (0, 0, {'employee_id': employee.id})
                for employee in self.env['hr.employee'].search(
                    [('company_id', '=', record.company_id.id), ('sale_objective', '=', True)]
                )
            ]
            record.objective_line_ids = line_vals

        return res
