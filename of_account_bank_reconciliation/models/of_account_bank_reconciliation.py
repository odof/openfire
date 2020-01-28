# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError

class OfAccountBankReconciliation(models.Model):
    _name = 'of.account.bank.reconciliation'
    _description = "Rapprochement bancaire OpenFire"
    _order = "date DESC, id DESC"

    name = fields.Char(
        string="Nom", required=True,
        readonly=True, states={'open': [('readonly', False)]}
    )
    company_id = fields.Many2one(
        'res.company', string=u'Société', required=True,
        readonly=True, states={'open': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice')
    )
    amount_total_prec = fields.Monetary(
        currency_field='currency_id', string=u'Solde relevé précédent',
        compute="_compute_amount_total_prec"
    )
    amount_total = fields.Monetary(
        currency_field='currency_id', string=u'Solde relevé en cours', required=True,
        readonly=True, states={'open': [('readonly', False)]}
    )
    amount_account = fields.Monetary(
        currency_field='currency_id', string='Solde compte', compute='_compute_amount_account',
        help=u"Total des écritures du compte à la date."
    )
    amount_lines = fields.Monetary(
        currency_field='currency_id', string=u'Total sélection', compute='_compute_amount',
        help=u"Total des écritures sélectionnées pour ce rapprochement."
    )
    amount_diff = fields.Monetary(currency_field='currency_id', string=u'Écart', compute='_compute_amount')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
        readonly=True, states={'open': [('readonly', False)]}
    )
    date = fields.Date(string="Date", required=True, readonly=True, states={'open': [('readonly', False)]})
    account_id = fields.Many2one(
        'account.account', string="Compte", required=True,
        readonly=True, states={'open': [('readonly', False)]}
    )
    move_line_ids = fields.One2many(
        'account.move.line', 'of_reconciliation_id', string=u"Écritures",
        readonly=True, states={'open': [('readonly', False)]}
    )
    note = fields.Text(string="Notes", readonly=True, states={'open': [('readonly', False)]})
    state = fields.Selection([('open', 'Ouvert'), ('done', 'Fait')], required=True, default='open')

    @api.depends('account_id', 'date')
    def _compute_amount_total_prec(self):
        for rec in self:
            if rec.date and rec.account_id:
                if isinstance(rec.id, (int, long)):
                    domain = [('account_id', '=', rec.account_id.id), '|', ('date', '<', rec.date), '&', ('date', '=', rec.date), ('id', '<', rec.id)]
                else:
                    domain = [('account_id', '=', rec.account_id.id), ('date', '<=', rec.date)]
                rec_prec = self.search(domain, limit=1)
                rec.amount_total_prec = rec_prec and rec_prec.amount_total or 0.0
            else:
                rec.amount_total_prec = 0.0

    @api.depends('account_id', 'date')
    def _compute_amount_account(self):
        for rec in self:
            if rec.date and rec.account_id:
                move_lines = self.env['account.move.line'].search([('account_id', '=', rec.account_id.id), ('date', '<=', rec.date)])
                rec.amount_account = sum(move_line.balance for move_line in move_lines)
            else:
                rec.amount_account = 0.0

    @api.depends('move_line_ids', 'amount_total_prec', 'amount_total')
    def _compute_amount(self):
        for rec in self:
            rec.amount_lines = sum(rec.move_line_ids.mapped('balance'))
            rec.amount_diff = rec.amount_total - rec.amount_total_prec - rec.amount_lines

    @api.multi
    def action_open(self):
        self.write({'state': 'open'})

    @api.multi
    def action_done(self):
        for rec in self:
            if rec.amount_diff:
                raise UserError(u'Vous ne pouvez pas valider un rapprochement bancaire avec un écart.')
        self.write({'state': 'done'})

    @api.model
    def create(self, vals):
        """ Mettre check_move_validity = False dans le contexte
        pour pouvoir lier les écritures comptables avec le rapprochement bancaire.
        """
        return super(OfAccountBankReconciliation, self.with_context(check_move_validity=False)).create(vals)

    @api.multi
    def write(self, vals):
        """ Mettre check_move_validity = False dans le contexte
        pour pouvoir lier les écritures comptables avec le rapprochement bancaire.
        """
        return super(OfAccountBankReconciliation, self.with_context(check_move_validity=False)).write(vals)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    of_reconciliation_id = fields.Many2one('of.account.bank.reconciliation', string="Rapprochement bancaire", readonly=True)
