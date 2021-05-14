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

    of_contract_id = fields.Many2one('of.contract', string="Contrat")
    of_compute_contract_id = fields.Many2one(
        'of.contract', string="Contrat", compute='_compute_contract_id', inverse='_inverse_contract_id',
        help="Ce champ, s'il est rempli manuellement, n'aura pas d'incidence sur le contrat.")
    of_contract_period = fields.Char(string=u"Période du contrat", compute='_compute_of_contract_period')
    of_intervention_id = fields.Many2one('of.planning.intervention', string="RDV d'intervention")

    @api.depends('of_contract_id')
    def _compute_contract_id(self):
        for invoice in self:
            invoice.of_compute_contract_id = invoice.of_contract_id

    @api.multi
    def _inverse_contract_id(self):
        for invoice in self:
            invoice.of_contract_id = invoice.of_compute_contract_id

    @api.depends('of_contract_id', 'date_invoice', 'of_intervention_id')
    def _compute_of_contract_period(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for invoice in self:
            if invoice.of_contract_id and invoice.date_invoice:
                contractual_lines = invoice.invoice_line_ids.filtered('of_contract_line_id')
                if not contractual_lines:
                    continue
                # toutes les lignes doivent avoir la même date prévue ou la même fréquence de facturation
                if len(contractual_lines) > 1 and \
                    (not all(date == contractual_lines[0].of_contract_supposed_date
                             for date in contractual_lines.mapped('of_contract_supposed_date')) or
                     not all(code == contractual_lines[0].of_contract_line_id.frequency_type
                             for code in contractual_lines.mapped('of_contract_line_id').mapped('frequency_type'))):
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

    def _get_refund_common_fields(self):
        common_fields = ['of_contract_id']
        return (super(OfAccountInvoice, self)._get_refund_common_fields() or []) + common_fields

    def _get_refund_copy_fields(self):
        copy_fields = ['of_contract_id']
        return (super(OfAccountInvoice, self)._get_refund_copy_fields() or []) + copy_fields

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Surcharge pour que tout avoir soit pris en compte dans les contrats
        """
        result = super(OfAccountInvoice, self)._refund_cleanup_lines(lines)
        # le context mode n'est envoyé que pour la création de la nouvelle facture et non pour l'avoir
        if self.env.context.get('mode') == 'modify':
            for i in xrange(0, len(lines)):
                for name, field in lines[i]._fields.iteritems():
                    if name in ('of_contract_product_id', 'of_contract_line_id'):
                        # Par sécurité mais supposément non nécessaire
                        result[i][2][name] = lines[i][name] and lines[i][name].id or False
                        lines[i][name] = False
        elif self.env.context.get('of_mode') in ('refund', 'modify'):
            for i in xrange(0, len(lines)):
                for name, field in lines[i]._fields.iteritems():
                    if name in ('of_contract_product_id', 'of_contract_line_id'):
                        # La fonction d'origine copie tous les champs many2one y compris ceux en copy=False
                        # On ne veut pas que ce soit copié dans ce cas
                        result[i][2][name] = False
        elif self.env.context.get('of_mode') == 'cancel':
            for i in xrange(0, len(lines)):
                for name, field in lines[i]._fields.iteritems():
                    if name in ('of_contract_product_id', 'of_contract_line_id'):
                        lines[i][name] = False
                        # La fonction d'origine copie tous les champs many2one y compris ceux en copy=False
                        # On ne veut pas que ce soit copié dans ce cas
                        result[i][2][name] = False

        return result


class OfAccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    of_contract_id = fields.Many2one('of.contract', string="Contrat")
    of_contract_product_id = fields.Many2one('of.contract.product', string="Article contrat", copy=False)
    of_contract_line_id = fields.Many2one('of.contract.line', string="Ligne de contrat", copy=False)
    of_contract_supposed_date = fields.Date(string=u'Date prévue', readonly=True)
