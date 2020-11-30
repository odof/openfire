# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains('company_id', 'stock_location_id')
    def _check_company_location(self):
        if self.stock_location_id.company_id and self.stock_location_id.company_id.id not in \
                [self.company_id.id, self.company_id.accounting_company_id.id]:
            raise UserError(_("The company of the stock location is different than the one of point of sale"))

    @api.constrains('company_id', 'journal_id')
    def _check_company_journal(self):
        if self.journal_id and self.journal_id.company_id.id != self.company_id.accounting_company_id.id:
            raise UserError(_("The company of the sale journal is different than the one of point of sale"))

    @api.constrains('company_id', 'invoice_journal_id')
    def _check_company_invoice_journal(self):
        if self.invoice_journal_id and self.invoice_journal_id.company_id.id != \
                self.company_id.accounting_company_id.id:
            raise UserError(_("The invoice journal and the point of sale must belong to the same company"))

    @api.constrains('company_id', 'journal_ids')
    def _check_company_payment(self):
        if self.env['account.journal'].search_count(
                [('id', 'in', self.journal_ids.ids),
                 ('company_id', 'not in', (self.company_id.id, self.company_id.accounting_company_id.id))]):
            raise UserError(_("The company of a payment method is different than the one of point of sale"))
