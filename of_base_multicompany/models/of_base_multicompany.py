# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.addons.account.models.account_invoice import TYPE2JOURNAL

class Company(models.Model):
    _inherit = 'res.company'

    accounting_company_id = fields.Many2one(
        'res.company', compute='_compute_accounting_company', string=u"Société comptable",
        help=u"Pour un magasin, ce champ référence la société associée, qui gère le plan comptable.\n"
             u"Pour une société disposant d'un plan comptable, ce champ référence la société elle-même.")

    @api.multi
    @api.depends('chart_template_id', 'parent_id', 'parent_id.accounting_company_id')
    def _compute_accounting_company(self):
        self.ensure_one()
        for company in self:
            accounting_company = company
            while not accounting_company.chart_template_id and accounting_company.parent_id:
                accounting_company = accounting_company.parent_id
            company.accounting_company_id = accounting_company

    @api.model
    def _company_default_get(self, object=False, field=False):
        res = super(Company, self)._company_default_get(object, field)
        # Dans le cadre de la recherche d'un compte comptable, la société voulue est la société comptable.
        if object == 'account.account' and not field:
            res = res.accounting_company_id
        return res

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _default_journal(self):
        journal = super(AccountInvoice, self)._default_journal()
        # Code modifié de la fonction account_invoice._default_journal() pour recherche sur la société comptable
        if not journal:
            company_id = self._context.get('company_id', self.env.user.company_id.id)
            company = self.env['res.company'].browse(company_id)
            if company != company.accounting_company_id:
                # Code copié de account.invoice._default_journal() définie dans le module account
                inv_type = self._context.get('type', 'out_invoice')
                inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
                domain = [
                    ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
                    ('company_id', '=', company.accounting_company_id.id),
                ]
                journal = self.env['account.journal'].search(domain, limit=1)
        return journal

    accounting_company_id = fields.Many2one(
        'res.company', related='company_id.accounting_company_id', string=u"Société comptable")
    journal_id = fields.Many2one('account.journal',
        default=lambda self: self._default_journal(),
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', 'in', (company_id, accounting_company_id))]")

class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            vals['company_id'] = self.env['res.company'].browse(vals['company_id']).accounting_company_id.id
        return super(AccountAccount, self).create(vals)

class AccountMove(models.Model):
    _inherit = 'account.move'

    # La société de la pièce comptable doit être la même que celle des écritures (voir account.move._post_validate())
    company_id = fields.Many2one('res.company', related='journal_id.company_id.accounting_company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env.user.company_id.accounting_company_id)

class Property(models.Model):
    _inherit = 'ir.property'

    def _get_domain(self, prop_name, model):
        res = super(Property, self)._get_domain(prop_name, model)
        if res:
            # Part du principe que _get_domain renvoie un domaine de la forme [(...), ('company_id', 'in', [company_id, False])]
            company = self.env['res.company'].browse(res[1][2][0])
            res[1][2][0] = company.accounting_company_id.id
        return res

    @api.model
    def set_multi(self, name, model, values, default_value=None):
        # retrieve the properties corresponding to the given record ids
        self._cr.execute("SELECT id FROM ir_model_fields WHERE name=%s AND model=%s", (name, model))
        field_id = self._cr.fetchone()[0]
        company_id = self.env.context.get('force_company') or self.env['res.company']._company_default_get(model, field_id).id
        company = self.env['res.company'].browse(company_id)
        self = self.with_context(force_company=company.accounting_company_id.id)
        return super(Property, self).set_multi(name, model, values, default_value=default_value)
