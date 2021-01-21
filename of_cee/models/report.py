# -*- coding: utf-8 -*-

from odoo import api, models, fields


class Report(models.Model):
    _inherit = 'report'

    @api.multi
    def render(self, template, values=None):
        if template == 'account.report_invoice' and values.get('doc_ids', False):
            invoice = self.env['account.invoice'].browse(values['doc_ids'][0])
            if invoice.of_is_cee and invoice.partner_id.of_cee_invoice_template:
                template = invoice.partner_id.of_cee_invoice_template
        return super(Report, self).render(template, values=values)
