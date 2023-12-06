# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class OFContractInvoicingWizard(models.TransientModel):
    _name = 'of.contract.invoicing.wizard'

    def _default_contract(self):
        ids = self._context.get('active_ids')
        if not ids:
            return
        return self.env['of.contract'].browse(ids[0])

    contract_id = fields.Many2one(
        comodel_name='of.contract', string=u"Contrat", ondelete='cascade',
        default=lambda self: self._default_contract()
    )
    invoicing_period = fields.Date(string=u"Période de facturation", required=True)
    invoicing_method = fields.Selection(selection=
        [
            ('day', u"Date du jour"),
            ('computed', u"Date calculée"),
            ('manual', u"Manuelle"),
        ], string=u"Méthode de facturation", required=True)
    manual_date = fields.Date(string=u"Date de facturation")
    line_ids = fields.One2many(
        comodel_name='of.contract.invoicing.line.wizard', inverse_name='wizard_id', string=u"Lignes à facturer")

    @api.multi
    def compute_line_ids(self):
        lines = [(5, )]
        for line in self.contract_id.line_ids:
            if line.next_date and line.next_date <= self.invoicing_period:
                lines.append((0, 0, {
                    'wizard_id': self.id,
                    'contract_line_id': line.id,
                    'selected': True,
                }))
        self.write({'line_ids': lines})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def select_all(self):
        self.line_ids.update({'selected': True})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def deselect_all(self):
        self.line_ids.update({'selected': False})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_apply(self):
        lines_selected = self.line_ids.filtered('selected').mapped('contract_line_id')
        invoices = self.env['account.invoice']
        with self.env.norecompute():
            if self.invoicing_method == 'computed':
                dates = lines_selected.mapped('next_date')
                dates.sort()
                for date in dates:
                    lines = lines_selected.filtered(lambda l: l.next_date == date)
                    invoices += self._create_invoice(self.with_context(force_date=date).contract_id, lines)
            else:
                date = self.invoicing_method == 'day' and fields.Date.today() or self.manual_date
                invoices = self._create_invoice(self.with_context(force_date=date).contract_id, lines_selected)
        self.contract_id.recompute()
        self.lines_selected._auto_cancel()
        return self.contract_id.action_view_invoice()

    @api.multi
    def _create_invoice(self, contract, lines, do_raise=True):
        """ Création des factures du contrats en fonction de si les lignes du contrat sont groupées ou non """
        contract.ensure_one()
        if not lines:
            if do_raise:
                raise UserError("Aucune ligne du contrat n'est facturable")
            else:
                contract.message_post(body=u"Création de la facture : Aucune ligne du contrat n'est facturable.")
                return False
        lines_grouped = lines.filtered('grouped')
        single_lines = lines - lines_grouped
        invoices = contract.env['account.invoice']
        if lines_grouped:
            invoice_vals = contract._prepare_invoice(do_raise=do_raise)
            if not invoice_vals:
                return invoices
            lines = []
            for line in lines_grouped:
                lines += line._add_invoice_lines()
            if lines:
                addresses = lines_grouped.mapped('address_id')
                if len(addresses) == 1:
                    invoice_vals['partner_shipping_id'] = addresses.id
                invoice_vals['invoice_line_ids'] = lines
                invoice = contract.env['account.invoice'].create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
        if single_lines:
            for line in single_lines:
                intervention_id = False
                if line.frequency_type == 'date':
                    last_invoicing = line.last_invoicing_date
                    if not last_invoicing:
                        date_start = fields.Date.from_string(line.date_contract_start)
                        last_invoicing = fields.Date.to_string(date_start - relativedelta(days=1))
                    interventions = line.intervention_ids.filtered(
                        lambda i: i.state == 'done' and i.date_date > last_invoicing)
                    if interventions:
                        interventions = interventions.sorted('date_date')
                        intervention_id = interventions[0].id
                invoice_vals = contract._prepare_invoice(do_raise=do_raise, intervention_id=intervention_id)
                if not invoice_vals:
                    continue
                lines = line._add_invoice_lines()
                if not lines:
                    continue
                if line.address_id:
                    invoice_vals['partner_shipping_id'] = line.address_id.id
                invoice_vals['invoice_line_ids'] = lines
                invoice = contract.env['account.invoice'].create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
        return invoices


class OFContractInvoicingLineWizard(models.TransientModel):
    _name ='of.contract.invoicing.line.wizard'

    wizard_id = fields.Many2one(comodel_name='of.contract.invoicing.wizard', string="wizard", ondelete='cascade')
    contract_line_id = fields.Many2one(comodel_name='of.contract.line', string=u"Ligne de contrat")
    selected = fields.Boolean(string=u"À facturer")
    line_code = fields.Char(string=u"Code", related='contract_line_id.code_de_ligne', readonly=True)
    line_address_id = fields.Many2one(
        string=u"Adresse d'intervention", related='contract_line_id.address_id', readonly=True)
    line_address_zip = fields.Char(string=u"CP", related='contract_line_id.address_zip', readonly=True)
    line_address_city = fields.Char(string=u"Ville", related='contract_line_id.address_city', readonly=True)
    line_supplier_id = fields.Many2one(
        comodel_name='res.partner', string=u"Prestataire", related='contract_line_id.supplier_id', readonly=True)
    line_tache_id = fields.Many2one(
        comodel_name='of.planning.tache', string=u"Tâche", related='contract_line_id.tache_id', readonly=True)
    line_next_date = fields.Date(
        string=u"Date de prochaine facturation", related='contract_line_id.next_date', readonly=True)
    line_frequency_type = fields.Selection(
        string=u"Fréquence de facturation", related='contract_line_id.frequency_type', readonly=True)
    line_type = fields.Selection(string=u"Type de facturation", related='contract_line_id.type', readonly=True)
    line_company_currency_id = fields.Many2one(
        comodel_name='res.currency', string=u"Company Currency", related='contract_line_id.company_currency_id',
        readonly=True
    )
    line_amount_total = fields.Monetary(
        string=u"Montant de la prochaine facture", related='contract_line_id.amount_total', readonly=True,
        currency_field='line_company_currency_id'
    )
    line_grouped = fields.Boolean(string=u"Grouper les factures", related='contract_line_id.grouped', readonly=True)
