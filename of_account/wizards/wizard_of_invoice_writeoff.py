# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class OfWizardInvoiceWriteoff(models.TransientModel):
    _name = 'of.wizard.invoice.writeoff'

    invoice_ids = fields.Many2many('account.invoice', string="Factures", default=lambda s: s._default_invoice_ids())
    name = fields.Char(string="Libellé", required=True)
    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True,
        default=lambda s: s._default_journal_id(),
    )
    company_id = fields.Many2one('res.company', string=u"Société", compute='_compute_values')
    date = fields.Date(string=u"Date de la pièce", default=fields.Date.today)
    credit = fields.Float(u"Total au crédit", compute='_compute_values')
    debit = fields.Float(u"Total au débit", compute='_compute_values')
    residual = fields.Float(string="Balance", compute='_compute_values')
    account_debit_id = fields.Many2one(
        'account.account', string="Compte de profits", required=True,
        default=lambda s: s._default_account_debit_id())
    account_credit_id = fields.Many2one(
        'account.account', string="Compte de pertes", required=True,
        default=lambda s: s._default_account_credit_id())

    @api.model
    def _default_invoice_ids(self):
        return self.env['account.invoice'].browse(self._context.get('active_ids', []))

    @api.model
    def _default_journal_id(self):
        return self.env['account.journal'].search([('type', '=', 'general')], limit=1)

    @api.depends('invoice_ids')
    def _compute_values(self):
        invoices = self.invoice_ids
        inv_cred = invoices.filtered(lambda i: i.type in ('in_invoice', 'out_refund'))
        inv_deb = invoices - inv_cred
        self.credit = sum(inv_cred.mapped('residual'))
        self.debit = sum(inv_deb.mapped('residual'))
        self.residual = self.debit - self.credit
        self.company_id = self._get_company(invoices)

    @api.model
    def _get_company(self, invoices):
        accounting_company = invoices.mapped('company_id')
        if hasattr(accounting_company, 'accounting_company_id'):
            accounting_company = accounting_company.mapped('accounting_company_id')
        if len(accounting_company) > 1:
            raise UserError(u"Vous ne pouvez pas sélectionner plusieurs factures de sociétés différentes")
        return accounting_company

    @api.model
    def _default_account_credit_id(self):
        invoices = self.env['account.invoice'].browse(self._context.get('active_ids', []))
        company = self._get_company(invoices)
        return self.env['account.account'].search(
            [('company_id', '=', company.id),
             ('code', '=like', '658%')],
            limit=1)

    @api.model
    def _default_account_debit_id(self):
        invoices = self.env['account.invoice'].browse(self._context.get('active_ids', []))
        company = self._get_company(invoices)
        return self.env['account.account'].search(
            [('company_id', '=', company.id),
             ('code', '=like', '758%')],
            limit=1)

    @api.multi
    def _get_move_vals(self, journal=None):
        """ Return dict to create the writeoff move
        """
        journal = journal or self.journal_id
        return {
            'date': self.date,
            'ref': self.name or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }

    @api.multi
    def get_move_line_vals(self, move, move_lines, cur):
        residual = sum(move_lines.mapped('amount_residual'))
        if cur.is_zero(residual):
            return False
        return {
            'name': self.name,
            'move_id': move.id,
            'account_id': move_lines[0].account_id.id,
            'debit': residual < 0 and -residual,
            'credit': residual > 0 and residual,
        }

    @api.multi
    def get_move_line_writeoff_vals(self, move, balance, cur):
        if cur.is_zero(balance):
            return False
        return {
            'name': self.name,
            'move_id': move.id,
            'account_id': self.account_credit_id.id if balance < 0 else self.account_debit_id.id,
            'debit': balance < 0 and -balance,
            'credit': balance > 0 and balance,
        }

    @api.multi
    def action_process(self):
        self.ensure_one()
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoices = self.invoice_ids
        cur = invoices[0].company_id.currency_id

        # Regroupement des lignes par compte comptable
        account_move_lines = {}
        for invoice in invoices:
            for line in invoice.move_id.line_ids:
                if line.account_id.internal_type in ('receivable', 'payable') and not line.reconciled:
                    if line.account_id in account_move_lines:
                        account_move_lines[line.account_id] |= line
                    else:
                        account_move_lines[line.account_id] = line

        move = self.env['account.move'].create(self._get_move_vals(self.journal_id))

        balance = 0.0
        for account, move_lines in account_move_lines.iteritems():
            line_vals = self.get_move_line_vals(move, move_lines, cur)
            if line_vals:
                line = aml_obj.create(line_vals)
                move_lines |= line
                balance += line.balance
            move_lines.reconcile()

        if move.line_ids:
            # Création de l'écriture de contrepartie
            line_vals = self.get_move_line_writeoff_vals(move, balance, cur)
            if line_vals:
                aml_obj.create(line_vals)
            move.post()
        else:
            move.unlink()
