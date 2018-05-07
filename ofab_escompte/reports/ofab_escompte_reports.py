# -*- coding: utf-8 -*-

from odoo import models, fields, api
from itertools import groupby

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_invoice_line_sans_escompte_ids = fields.One2many('account.invoice.line', compute='_compute_of_invoice_line_escompte_ids')
    of_invoice_line_escompte_ids = fields.One2many('account.invoice.line', compute='_compute_of_invoice_line_escompte_ids')
    of_total_amount_escompte = fields.Float(string="Escompte", compute='_compute_of_invoice_line_escompte_ids')

    @api.depends('invoice_line_ids')
    def _compute_of_invoice_line_escompte_ids(self):
        for invoice in self:
            self.of_invoice_line_escompte_ids = self.invoice_line_ids.filtered(lambda line: line.of_type_escompte)
            self.of_invoice_line_sans_escompte_ids = self.invoice_line_ids - self.of_invoice_line_escompte_ids

            of_total_amount_escompte = 0
            for escompte in invoice.of_invoice_line_escompte_ids:
                of_total_amount_escompte += float(escompte.price_subtotal)
            invoice.of_total_amount_escompte = float(of_total_amount_escompte)
