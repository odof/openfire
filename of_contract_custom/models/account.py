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
                contractual_lines = invoice.invoice_line_ids.filtered('of_contract_line_id')
                if len(contractual_lines) > 1 and not all([date == contractual_lines[0].of_contract_supposed_date for date in contractual_lines.mapped('of_contract_supposed_date')]):
                    continue
                base_date = contractual_lines[0].of_contract_supposed_date
                recurring_invoicing_payment = invoice.of_contract_id.recurring_invoicing_payment_id
                recurring_rule_type = invoice.of_contract_id.recurring_rule_type
                months = month_correspondance[recurring_rule_type]
                if recurring_invoicing_payment.code == 'pre-paid':
                    if not months and invoice.of_intervention_id:
                        invoice.of_contract_period = u"Facturation à date %s" % format_date(
                                invoice.of_intervention_id.date_date, lang)
                    else:
                        date = fields.Date.from_string(base_date)
                        period_end = date + relativedelta(months=months, days=-1)
                        invoice.of_contract_period = "%s - %s" % (format_date(base_date, lang),
                                                                  format_date(fields.Date.to_string(period_end), lang))
                else:
                    if not months and invoice.of_intervention_id:
                        invoice.of_contract_period = u"Facturation à date %s" % format_date(
                                invoice.of_intervention_id.date_date, lang)
                    else:
                        months = -(months-1)
                        date = fields.Date.from_string(base_date)
                        if recurring_rule_type == 'date':
                            period_start = date + relativedelta(day=1)
                        else:
                            period_start = date + relativedelta(months=months, day=1)

                        invoice.of_contract_period = "%s - %s" % (
                            format_date(fields.Date.to_string(period_start), lang),
                            format_date(base_date, lang))


class OfAccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    of_contract_id = fields.Many2one('of.contract', string="(OF) Contrat")
    of_contract_product_id = fields.Many2one('of.contract.product', string="(OF) Article contrat")
    of_contract_line_id = fields.Many2one('of.contract.line', string="(OF) Ligne de contrat")
    of_contract_supposed_date = fields.Date(string=u'Date prévue', readonly=True)
