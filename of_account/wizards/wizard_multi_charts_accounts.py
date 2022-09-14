# -*- coding: utf-8 -*-

from odoo import models, api


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def execute(self):
        res = super(WizardMultiChartsAccounts, self).execute()

        # Le plan comptable vient d'être créé, on verrouille les compte 401100 et 411100
        property_obj = self.env['ir.property'].sudo().with_context(force_company=self.company_id.id)
        default_account_receivable = property_obj.get('property_account_receivable_id', 'res.partner')
        default_account_payable = property_obj.get('property_account_payable_id', 'res.partner')
        (default_account_receivable | default_account_payable).write({'of_editable': False})

        return res
