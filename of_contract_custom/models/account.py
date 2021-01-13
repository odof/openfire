# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.of_utils.models.of_utils import format_date
from dateutil.relativedelta import relativedelta

month_correspondance = {
    'date': 0,
    'month': 1,
    'trimester': 3,  # Tout les 3 mois
    'semester': 6,  # 2 fois par ans
    'year': 12,
}


class OfAccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_contract_id = fields.Many2one('of.contract', string="(OF) Contrat")
    of_contract_period = fields.Char(string=u"Période du contrat", compute='_compute_of_contract_period')
    of_intervention_id = fields.Many2one('of.planning.intervention', string="RDV d'intervention")

    @api.depends('of_contract_id', 'date_invoice', 'of_intervention_id')
    def _compute_of_contract_period(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for invoice in self:
            if invoice.of_contract_id and invoice.date_invoice:
                recurring_invoicing_payment = invoice.of_contract_id.recurring_invoicing_payment_id
                recurring_rule_type = invoice.of_contract_id.recurring_rule_type
                months = month_correspondance[recurring_rule_type]
                if recurring_invoicing_payment.code == 'pre-paid':
                    if not months and invoice.of_intervention_id:
                        invoice.of_contract_period = u"Facturation à date %s" % format_date(invoice.of_intervention_id.date_date, lang)
                    else:
                        date = fields.Date.from_string(invoice.date_invoice)
                        period_end = date + relativedelta(months=months, days=-1)
                        invoice.of_contract_period = "%s - %s" % (format_date(invoice.date_invoice, lang),
                                                                  format_date(fields.Date.to_string(period_end), lang))
                else:
                    if not months and invoice.of_intervention_id:
                        invoice.of_contract_period = u"Facturation à date %s" % format_date(invoice.of_intervention_id.date_date, lang)
                    else:
                        months = -months
                        date = fields.Date.from_string(invoice.date_invoice)
                        period_start = date + relativedelta(months=months, days=1)
                        invoice.of_contract_period = "%s - %s" % (format_date(fields.Date.to_string(period_start), lang),
                                                                  format_date(invoice.date_invoice, lang))


class OfAccountInvoiceLine(models.Model):

    _inherit = "account.invoice.line"

    of_contract_id = fields.Many2one('of.contract', string="(OF) Contrat")
    of_contract_product_id = fields.Many2one('of.contract.product', string="(OF) Article contrat")
    of_contract_line_id = fields.Many2one('of.contract.line', string="(OF) Ligne de contrat")

