# -*- coding: utf-8 -*-

from odoo import models

class OfContractInvoiceConfirm(models.TransientModel):
    _name = 'of.contract.invoice.confirm'
    _description = u"Wizard de confirmation de génération de factures"

    def action_create_invoices(self):
        self.env['account.analytic.account'].browse(self._context['active_ids']).recurring_create_invoice()
