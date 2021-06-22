# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date


def get_years():
    year_list = []
    for i in range(2020, 2031):
        year_list.append((i, str(i)))
    return year_list


class OFSaleObjective(models.Model):
    """Objectif mensuel de ventes"""

    _name = 'of.sale.objective'
    _description = "Objectif mensuel de ventes"
    _order = 'year desc, month desc'

    company_id = fields.Many2one(comodel_name='res.company', string=u"Magasin", required=True)
    month = fields.Selection(
        selection=[('01', u"Janvier"),
                   ('02', u"Février"),
                   ('03', u"Mars"),
                   ('04', u"Avril"),
                   ('05', u"Mai"),
                   ('06', u"Juin"),
                   ('07', u"Juillet"),
                   ('08', u"Août"),
                   ('09', u"Septembre"),
                   ('10', u"Octobre"),
                   ('11', u"Novembre"),
                   ('12', u"Décembre")], string=u"Mois", required=True)
    year = fields.Selection(selection=get_years(), string=u"Année", required=True)
    objective_line_ids = fields.One2many(
        comodel_name='of.sale.objective.line', inverse_name='objective_id', string=u"Lignes d'objectif")
    objective_date = fields.Date(string="Date objectif", compute="_compute_objective_date", store=True)

    @api.depends('month', 'year')
    def _compute_objective_date(self):
        for objective in self:
            objective.objective_date = fields.Date.to_string(
                    date(year=objective.year, month=int(objective.month), day=1))

    @api.multi
    def name_get(self):
        res = []
        for obj in self:
            res.append((obj.id, '%s - %s %s' % (obj.company_id.name, obj.month, obj.year)))
        return res

    @api.model
    def create(self, vals):
        # On vérifie qu'un objectif mensuel n'existe pas déjà pour ce magasin et ce mois
        if self.search([('company_id', '=', vals.get('company_id')),
                        ('month', '=', vals.get('month')),
                        ('year', '=', vals.get('year'))]):
            raise UserError(u"Un objectif mensuel a déjà été défini pour ce magasin et ce mois !")

        res = super(OFSaleObjective, self).create(vals)

        # On crée les lignes d'objectif pour tous les vendeurs du magasin
        line_vals = []
        for employee in self.env['hr.employee'].search(
                [('company_id', '=', res.company_id.id), ('sale_objective', '=', True)]):
            line_vals.append((0, 0, {'employee_id': employee.id}))
        res.objective_line_ids = line_vals

        return res


class OFSaleObjectiveLine(models.Model):
    """Ligne d'objectif mensuel de ventes"""

    _name = 'of.sale.objective.line'
    _description = "Ligne d'objectif mensuel de ventes"
    _order = 'employee_id'

    objective_id = fields.Many2one(
        comodel_name='of.sale.objective', string=u"Objectif mensuel associé", required=True, ondelete='cascade')
    employee_id = fields.Many2one(comodel_name='hr.employee', string=u"Vendeur", required=True)
    turnover_budget = fields.Float(string=u"Budget CA")
    ordered_turnover = fields.Float(string=u"CA commandé")
    invoiced_turnover = fields.Float(string=u"CA facturé")

    _sql_constraints = [
        ('of_sale_objective_line_employee_uniq',
         'unique (objective_id, employee_id)',
         u"Un même employé ne peut avoir deux objectifs pour le même mois !")
    ]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sale_objective = fields.Boolean(
        string=u"Objectifs de ventes", help=u"Indique si des objectifs de ventes doivent être définis pour cet employé")
