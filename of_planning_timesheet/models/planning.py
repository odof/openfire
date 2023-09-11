# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    of_analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='of_intervention_id', string=u"Temps")
    of_account_id = fields.Many2one(
        comodel_name='account.analytic.account', string=u"Compte analytique", compute='_compute_of_account_id')

    @api.depends('partner_id', 'order_id', 'company_id')
    def _compute_of_account_id(self):
        analytic_obj = self.env['account.analytic.account']
        for intervention in self:
            account = False
            if intervention.order_id:
                account = intervention.order_id.project_id
            if not account and intervention.partner_id:
                account = analytic_obj.search([('partner_id', '=', intervention.partner_id.id)])
            if not account:
                account = intervention.company_id.of_account_id
            if account:
                intervention.of_account_id = account[0].id

    @api.onchange('address_id')
    def _onchange_address_id(self):
        res = super(OFPlanningIntervention,self)._onchange_address_id()
        for line in self.of_analytic_line_ids:
            line._onchange_of_intervention_id()
        return res

    @api.model
    def create(self, vals):
        analytic_line_obj = self.env['account.analytic.line'].sudo()
        res = super(OFPlanningIntervention, self).create(vals)

        if vals.get('employee_ids'):
            user_to_add = res.employee_ids.mapped('user_id')

            for user in user_to_add:
                analytic_line_obj.create({
                    'of_intervention_id': res.id,
                    'name': res.name,
                    'date': res.date,
                    'partner_id': res.partner_id.id,
                    'user_id': user.id,
                    'of_state': 'draft',
                    'account_id': res.of_account_id.id,
                })

        return res

    @api.multi
    def write(self, vals):
        employee_obj = self.env['hr.employee']
        analytic_line_obj = self.env['account.analytic.line']

        if vals.get('of_analytic_line_ids'):
            try:
                for line in vals['of_analytic_line_ids']:
                    if line[2]:
                        analytic_line_obj.browse(line[1]).check_access_rule('write')
            except Exception:
                raise UserError(_(u"Vous ne pouvez pas modifier les feuilles de temps d'autre personne"))

        res = super(OFPlanningIntervention, self).write(vals)

        if vals.get('employee_ids'):
            employee_ids = vals['employee_ids'] and vals['employee_ids'][0] and vals['employee_ids'][0][2]
            employees = employee_obj.browse(employee_ids)
            users = employees.mapped('user_id')

            for intervention in self:
                user_to_add = users - intervention.of_analytic_line_ids.mapped('user_id')
                line_to_delete = intervention.of_analytic_line_ids.filtered(lambda x: x.user_id not in users)

                for user in user_to_add:
                    analytic_line_obj.sudo().create({
                        'of_intervention_id': intervention.id,
                        'name': intervention.name,
                        'partner_id': intervention.partner_id.id,
                        'user_id': user.id,
                        'of_state': 'draft',
                        'account_id': intervention.of_account_id.id,
                    })

                line_to_delete.sudo().unlink()

        return res

    @api.multi
    def validate_of_analytic_line_ids(self):
        self.mapped('of_analytic_line_ids').write({'of_state': 'done'})
