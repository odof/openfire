# -*- coding: utf-8 -*-

from odoo import api, models, fields

class Company(models.Model):
    _inherit = 'res.company'

    @api.multi
    def _get_accounting_company(self):
        self.ensure_one()
        company = self
        while not company.chart_template_id and company.parent_id:
            company = company.parent_id
        return company

    @api.model
    def _company_default_get(self, object=False, field=False):
        res = super(Company, self)._company_default_get(object, field)
        if object == 'account.account' and not field:
            res = res._get_accounting_company()
        return res

class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            vals['company_id'] = self.env['res.company'].browse(vals['company_id'])._get_accounting_company().id
        return super(AccountAccount, self).create(vals)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    company_id = fields.Many2one('res.company', related='move_id.journal_id.company_id', string='Company', store=True, readonly=True)

class Property(models.Model):
    _inherit = 'ir.property'

    def _get_domain(self, prop_name, model):
        res = super(Property, self)._get_domain(prop_name, model)
        if res:
            # Part du principe que _get_domain renvoie un domaine de la forme [(...), ('company_id', 'in', [company_id, False])]
            company = self.env['res.company'].browse(res[1][2][0])
            res[1][2][0] = company._get_accounting_company().id
        return res

    @api.model
    def set_multi(self, name, model, values, default_value=None):
        # retrieve the properties corresponding to the given record ids
        self._cr.execute("SELECT id FROM ir_model_fields WHERE name=%s AND model=%s", (name, model))
        field_id = self._cr.fetchone()[0]
        company_id = self.env.context.get('force_company') or self.env['res.company']._company_default_get(model, field_id).id
        company = self.env['res.company'].browse(company_id)
        self = self.with_context(force_company=company._get_accounting_company().id)
        return super(Property, self).set_multi(name, model, values, default_value=default_value)
