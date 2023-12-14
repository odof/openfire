# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api
from odoo.tools import float_compare
import odoo.addons.decimal_precision as dp


class OFAccountEcheance(models.Model):
    _name = "of.account.echeance"
    _order = "invoice_id, sequence, id"

    name = fields.Char(string=u"Nom", required=True, default=u"Échéance")
    invoice_id = fields.Many2one(comodel_name='account.invoice', string=u"Facture")
    currency_id = fields.Many2one(related='invoice_id.currency_id', readonly=True)
    amount = fields.Monetary(string=u"Montant", currency_field='currency_id')
    percent = fields.Float(string=u"Pourcentage", digits=dp.get_precision('Product Price'))
    last = fields.Boolean(string=u"Dernière Échéance", compute='_compute_last')

    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of payment term lines.")
    date = fields.Date(string=u"Date")

    @api.multi
    def _compute_last(self):
        for invoice in self.mapped('invoice_id'):
            for echeance in invoice.of_echeance_line_ids:
                echeance.last = echeance == invoice.of_echeance_line_ids[-1]

    @api.onchange("amount")
    def _onchange_amount(self):
        """Met à jour le pourcentage en fonction du montant"""
        invoice_amount = self._context.get('invoice_amount', self.invoice_id.amount_total)
        # Test: si le nouveau montant est calculé depuis le pourcentage, on ne le recalcule pas
        test_amount = invoice_amount * self.percent / 100
        if float_compare(self.amount, test_amount, precision_rounding=.01):
            self.percent = self.amount * 100 / invoice_amount if invoice_amount else 0

    @api.onchange("percent")
    def _onchange_percent(self):
        """Met à jour le montant en fonction du pourcentage"""
        invoice_amount = self._context.get('invoice_amount', self.invoice_id.amount_total)
        # Test: si le nouveau pourcentage est calculé depuis le montant, on ne le recalcule pas
        test_percent = self.amount * 100 / invoice_amount if invoice_amount else 0
        if float_compare(self.percent, test_percent, precision_rounding=.01):
            self.amount = invoice_amount * self.percent / 100

    @api.multi
    def _get_totlines(self, date_invoice):
        return [(record.date or date_invoice, record.amount) for record in self]
