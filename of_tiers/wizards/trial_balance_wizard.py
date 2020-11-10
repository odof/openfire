# -*- coding: utf-8 -*-

from odoo import models, fields


class TrialBalanceReportWizard(models.TransientModel):
    _inherit = "trial.balance.report.wizard"

    def _default_of_receivable_account_id(self):
        return self.env['ir.property'].get('property_account_receivable_id', 'res.partner')

    def _default_of_payable_account_id(self):
        return self.env['ir.property'].get('property_account_payable_id', 'res.partner')

    of_receivable_accounts_grouped = fields.Boolean(string="Regrouper les comptes client")
    of_receivable_account_id = fields.Many2one(
        'account.account', string="Compte de regroupement",
        default=lambda s: s._default_of_receivable_account_id(),
        help=u"Compte sous lequel doivent s'afficher toutes les écritures"
    )
    of_payable_accounts_grouped = fields.Boolean(string="Regrouper les comptes fournisseur")
    of_payable_account_id = fields.Many2one(
        'account.account', string="Compte de regroupement",
        default=lambda s: s._default_of_payable_account_id(),
        help=u"Compte sous lequel doivent s'afficher toutes les écritures"
    )

    def _prepare_report_trial_balance(self):
        result = super(TrialBalanceReportWizard, self)._prepare_report_trial_balance()
        result.update({
            'of_receivable_account_id': self.of_receivable_accounts_grouped and self.of_receivable_account_id.id,
            'of_payable_account_id': self.of_payable_accounts_grouped and self.of_payable_account_id.id,
        })
        return result
