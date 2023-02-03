# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class AccountGroup(models.Model):
    _inherit = 'account.group'
    _order = 'sequence, code_prefix'

    code_prefix = fields.Char(
        string="Code prefixes", compute='_compute_code_prefix', inverse='_inverse_code_prefix',
        search='_search_code_prefix', store=True, help=u"Account code prefixes, separated by a comma.")
    sequence = fields.Integer(default=10)
    of_account_type_ids = fields.Many2many(
        comodel_name='account.account.type', string="Account types",
        help="Adds a filter on account types eligible for this group.")
    code_ids = fields.One2many(
        comodel_name='of.account.group.code', inverse_name='group_id')

    @api.depends('code_ids.code')
    def _compute_code_prefix(self):
        for group in self:
            group.code_prefix = ','.join(group.code_ids.mapped('code'))

    @api.multi
    def _inverse_code_prefix(self):
        for group in self:
            if not group.code_prefix:
                group.code_ids = [(5, )]
                continue
            codes_str = [c.strip() for c in group.code_prefix.split(',')]
            codes = group.code_ids
            existing_codes = codes.filtered(lambda c: c.code in codes_str)
            existing_codes_str = codes.mapped('code')

            # Codes déjà enregistrés
            # codes_data = [(4, c.id) for c in existing_codes]
            codes_data = []

            # Nouveaux codes ajoutés
            for cstr in codes_str:
                if cstr not in existing_codes_str:
                    codes_data.append((0, 0, {'code': cstr}))

            # Codes supprimés
            for code in codes - existing_codes:
                codes_data.append((3, code.id))

            if codes_data:
                group.code_ids = codes_data

    @api.model
    def _search_code_prefix(self, operator, value):
        return [('code_ids.code', operator, value)]

    @api.multi
    def of_action_recompute(self):
        account_obj = self.env['account.account']
        all_codes = self.env['of.account.group.code'].search([])
        for group in self:
            domain = []
            for code_str in group.code_ids.mapped('code'):
                # On ajoute le code dans les comptes à rechercher
                if domain:
                    domain = ['|'] + domain
                subdomain = [('code', '=like', code_str + '%')]
                # On retire de la recherche les codes d'autres groupes qui commencent par ``code_str``
                for other_code in all_codes:
                    if other_code.group_id != group and other_code.code.startswith(code_str):
                        subdomain = ['&'] + subdomain + ['!', ('code', '=like', other_code.code + '%')]
                domain += subdomain
            group.account_ids = account_obj.search(domain)


class OfAccountGroupCode(models.Model):
    _name = 'of.account.group.code'
    _order = 'code'

    code = fields.Char(string=u"Code", required=True)
    group_id = fields.Many2one(comodel_name='account.group', string=u"Groupe", required=True, ondelete='cascade')

    _sql_constraints = [('account_group_code_unique', 'unique(code)', "Another account already uses this prefix")]
