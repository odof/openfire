# -*- coding: utf-8 -*-

from odoo import models, fields


class TrialBalanceReport(models.TransientModel):
    _inherit = 'report_trial_balance_qweb'

    of_receivable_account_id = fields.Many2one('account.account', string="Regroupement des comptes client")
    of_payable_account_id = fields.Many2one('account.account', string="Regroupement des comptes fournisseur")

    def _prepare_report_general_ledger(self):
        result = super(TrialBalanceReport, self)._prepare_report_general_ledger()
        result.update({
            'of_receivable_account_id': self.of_receivable_account_id.id,
            'of_payable_account_id': self.of_payable_account_id.id,
        })
        return result
