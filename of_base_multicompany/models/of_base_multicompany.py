# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.addons.account.models.account_invoice import TYPE2JOURNAL
from odoo.exceptions import UserError


# @todo: Certains paramètres de la société (e.g. méthode d'arrondi des taxes) devraient être communs à la société


class Company(models.Model):
    _inherit = 'res.company'

    accounting_company_id = fields.Many2one(
        'res.company', compute='_compute_accounting_company', string=u"Société comptable",
        help=u"Pour un magasin, ce champ référence la société associée, qui gère le plan comptable.\n"
             u"Pour une société disposant d'un plan comptable, ce champ référence la société elle-même.")
    of_is_shop = fields.Boolean(
        string="Est un magasin", default=True,
        help="Laisser coché pour pouvoir utiliser cette société dans les bons de commande")
    of_default_shop_id = fields.Many2one(
        'res.company', string="Magasin par défaut", domain="[('of_is_shop','=',True)]",
        help="Si ce champ est renseigné, le magasin sera choisi par défaut en place de la société courante.")

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
        if not object:
            # Sans objet on ne sait pas quelles modifications apporter au résultat.
            return res
        # Dans le cadre de la recherche d'un compte comptable, la société voulue est la société comptable.
        if object == 'account.account' and not field:
            res = res.accounting_company_id
        if object == 'account.invoice' or not object.startswith('account.'):
            # A l'exception de la comptabilité, on ne souhaite pas proposer des sociétés qui ne sont pas des magasins.
            if res and not res.of_is_shop:
                res = res.of_default_shop_id
        return res

    @api.multi
    def _of_filter_taxes(self, taxes):
        if not self or not taxes:
            return taxes
        accounting_company = self.accounting_company_id
        return taxes.filtered(lambda tax: tax.company_id.accounting_company_id == accounting_company)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # Surcharge pour permettre d'ajouter le filtre sur les magasins dans d'autres modules sans lien de dépendance
        if self._context.get('of_filter_magasin'):
            args = args + [('of_is_shop', '=', True)]
        return super(Company, self)._search(
            args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)


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
    journal_id = fields.Many2one(
        'account.journal',
        default=lambda self: self._default_journal(),
        domain="[('type', 'in', {"
               "     'out_invoice': ['sale'],"
               "     'out_refund': ['sale'],"
               "     'in_refund': ['purchase'],"
               "     'in_invoice': ['purchase']"
               "   }.get(type, [])),"
               " ('company_id', 'in', (company_id, accounting_company_id))]")
    company_id = fields.Many2one(domain=lambda s: s._get_company_field_domain())

    @api.model
    def _get_company_field_domain(self):
        return "type in ('out_invoice', 'out_refund') and [('of_is_shop','=',True)] or []"


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
    company_id = fields.Many2one(
        related='journal_id.company_id.accounting_company_id',
        default=lambda self: self.env.user.company_id.accounting_company_id)

    @api.model
    def _move_reverse_prepare(self, date=False, journal=False,
                              move_prefix=False):
        u"""
        Surcharge de la fonction définie dans le module oca/account_financial_tools/account_reversal
        afin de permettre la création d'extourne quand le journal de la pièce appartient à un magasin
        """
        self.ensure_one()
        journal = journal or self.journal_id
        # OF Ligne modifiée :
        if journal.company_id.accounting_company_id != self.company_id.accounting_company_id:
            raise UserError(
                _("Wrong company Journal is '%s' but we have '%s'") % (
                    journal.company_id.name, self.company_id.name))
        ref = self.ref or move_prefix
        if move_prefix and move_prefix != ref:
            ref = ' '.join([move_prefix, ref])
        date = date or self.date
        move = self.copy_data()[0]
        move.update({
            'journal_id': journal.id,
            'date': date,
            'ref': ref,
            'to_be_reversed': False,
            'state': 'draft',
        })
        return move


class Property(models.Model):
    _inherit = 'ir.property'

    def _get_domain(self, prop_name, model):
        res = super(Property, self)._get_domain(prop_name, model)
        if res:
            # Part du principe que _get_domain renvoie un domaine de la forme :
            # [(...), ('company_id', 'in', [company_id, False])]
            company = self.env['res.company'].browse(res[1][2][0])
            res[1][2][0] = company.accounting_company_id.id
        return res

    @api.model
    def set_multi(self, name, model, values, default_value=None):
        # retrieve the properties corresponding to the given record ids
        self._cr.execute("SELECT id FROM ir_model_fields WHERE name=%s AND model=%s", (name, model))
        field_id = self._cr.fetchone()[0]
        company_id = self.env.context.get('force_company')\
            or self.env['res.company']._company_default_get(model, field_id).id
        company = self.env['res.company'].browse(company_id)
        self = self.with_context(force_company=company.accounting_company_id.id)
        return super(Property, self).set_multi(name, model, values, default_value=default_value)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _default_warehouse_id(self):
        # Modification pour utiliser la société par défaut de la commande
        # plutôt que la société courante de l'utilisateur
        company_id = self.default_get(['company_id'])['company_id']
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        return warehouse_id

    accounting_company_id = fields.Many2one(
        'res.company', related='company_id.accounting_company_id', string=u"Société comptable")
    company_id = fields.Many2one(domain="[('of_is_shop', '=', True)]")
    warehouse_id = fields.Many2one(default=lambda s: s._default_warehouse_id())
