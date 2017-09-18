# -*- coding: utf-8 -*-

from odoo import api, models

class Company(models.Model):
    _inherit = 'res.company'

    @api.multi
    def _get_accounting_company(self):
        self.ensure_one()
        company = self
        while not company.chart_template_id and company.parent_id:
            company = company.parent_id
        return company

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
