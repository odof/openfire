# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
import datetime
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
    exception_line_ids = fields.One2many(
        comodel_name='of.contract.invoicing.exception.wizard', inverse_name='wizard_id',
        string=u"Exceptions de facturation"
    )

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
    def select_all_line_ids(self):
        self.line_ids.update({'selected': True})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def deselect_all_line_ids(self):
        self.line_ids.update({'selected': False})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def compute_exception_line_ids(self):
        lines = [(5, )]
        for line in self.mapped('contract_id.line_ids.exception_line_ids').filtered(
                lambda r: r.state == '1-to_invoice' and r.date_invoice_next <= self.invoicing_period):
            lines.append((0, 0, {
                'wizard_id': self.id,
                'contract_exception_id': line.id,
                'selected': True,
            }))
        self.write({'exception_line_ids': lines})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def select_all_exception_line_ids(self):
        self.exception_line_ids.update({'selected': True})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def deselect_all_exception_line_ids(self):
        self.exception_line_ids.update({'selected': False})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_apply(self):
        lines_selected = self.line_ids.filtered('selected').mapped('contract_line_id')
        exceptions_selected = self.exception_line_ids.filtered('selected').mapped('contract_exception_id')
        invoices = self.env['account.invoice']
        exception_lines = exceptions_selected
        with self.env.norecompute():
            if self.invoicing_method == 'computed':
                dates = lines_selected.mapped('next_date')
                dates.sort()
                dates = list(set(dates))
                for date in dates:
                    lines = lines_selected.filtered(lambda l: l.next_date == date)
                    exception_lines = exceptions_selected.filtered(lambda r: r.line_id.id in lines.ids)
                    new_invoices, exception_lines = self._create_invoice(
                        self.with_context(force_date=date).contract_id, lines, exception_lines)
                    invoices += new_invoices
            else:
                date = self.invoicing_method == 'day' and fields.Date.today() or self.manual_date
                invoices, exception_lines = self._create_invoice(
                    self.with_context(force_date=date).contract_id,
                    lines_selected.with_context(force_date=self.invoicing_period), exceptions_selected)
        self._handle_exceptions(self.contract_id.with_context(force_date=self.manual_date or fields.Date.today()),
                                exception_lines)
        self.contract_id.recompute()
        lines_selected._auto_cancel()
        return self.contract_id.action_view_invoice()

    @api.multi
    def _create_invoice(self, contract, lines, exception_lines, do_raise=True):
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
        services = self.env['of.service']
        invoicing_method = self.invoicing_method
        if lines_grouped:
            invoice_vals = contract._prepare_invoice(do_raise=do_raise)
            if not invoice_vals:
                return invoices
            lines = []
            for line in lines_grouped:
                lines += line._add_invoice_lines()
                services_to_invoice = line._get_to_invoice_services()
                if services_to_invoice:
                    services |= services_to_invoice
            if invoicing_method != 'computed':
                lines += self._handle_multiple_invoices_from_line(lines_grouped)
            if lines:
                exceptions = exception_lines.filtered(
                    lambda r: r.line_id.id in lines_grouped._ids and
                    r.date_invoice_next <= invoice_vals.get('date_invoice'))
                exception_lines -= exceptions
                for exception in exceptions:
                    lines += exception._add_invoice_lines()
                addresses = lines_grouped.mapped('address_id')
                if len(addresses) == 1:
                    invoice_vals['partner_shipping_id'] = addresses.id
                invoice_vals['invoice_line_ids'] = lines
                invoice = contract.env['account.invoice'].create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
                services.write({'contract_invoice_id': invoice.id})
        if single_lines:
            date_stop = self.invoicing_period
            for line in single_lines:
                intervention_id = False
                last_invoicing_date = line.last_invoicing_date
                next_date = line.next_date
                while next_date and next_date < date_stop:
                    if line.frequency_type == 'date':
                        intervention_id = self._get_intervention_from_last_invoicing_date_date(
                            line, last_invoicing_date)
                    if invoicing_method == 'computed':
                        contract = contract.with_context(force_date=next_date)
                    invoice, exception_lines = self._create_invoice_single_line(
                        contract, line, intervention_id, next_date, exception_lines)
                    last_invoicing_date = next_date
                    next_date = self.date_from_line(line, next_date)
        return invoices, exception_lines

    def _get_intervention_from_last_invoicing_date_date(self, line, last_invoicing_date):
        intervention_id = False
        if not last_invoicing_date:
            date_start = fields.Date.from_string(line.date_contract_start)
            last_invoicing_date = fields.Date.to_string(date_start - relativedelta(days=1))
        interventions = line.intervention_ids.filtered(
            lambda i: i.state == 'done' and i.date_date > last_invoicing_date)
        if interventions:
            interventions = interventions.sorted('date_date')
            intervention_id = interventions[0].id
        return intervention_id

    def _create_invoice_single_line(self, contract, line, intervention_id, next_date, exception_lines):
        services = self.env['of.service']
        invoice_vals = contract._prepare_invoice(do_raise=False, intervention_id=intervention_id)
        if not invoice_vals:
            return {}
        lines = line._add_invoice_lines()
        if 'force_date' in line._context:
            line = line.with_context(force_date=next_date)
        services_to_invoice = line._get_to_invoice_services()
        if services_to_invoice:
            services = services_to_invoice
        for il in lines:
            il[2]['of_contract_supposed_date'] = next_date
        if not lines:
            return {}
        exceptions = exception_lines.filtered(lambda r: r.line_id.id == line.id and r.date_invoice_next <= next_date)
        exception_lines -= exceptions
        for exception in exceptions:
            lines += exception._add_invoice_lines()
        if line.address_id:
            invoice_vals['partner_shipping_id'] = line.address_id.id
        invoice_vals['invoice_line_ids'] = lines
        invoice = contract.env['account.invoice'].create(invoice_vals)
        invoice.compute_taxes()
        services.write({'contract_invoice_id': invoice.id})
        return invoice, exception_lines

    @api.multi
    def _handle_exceptions(self, contract, exception_lines):
        """ Création des factures du contrats en fonction de si les lignes du contrat sont groupées ou non """
        contract.ensure_one()
        if not exception_lines:
            return False
        lines_grouped = exception_lines.filtered('line_id.grouped')
        single_lines = exception_lines - lines_grouped
        invoices = contract.env['account.invoice']
        invoicing_method = self.invoicing_method
        if lines_grouped:
            invoice_vals = contract._prepare_invoice(do_raise=False)
            if not invoice_vals:
                return invoices
            lines = []
            for line in lines_grouped:
                lines += line._add_invoice_lines()
            if lines:
                addresses = lines_grouped.mapped('line_id.address_id')
                if len(addresses) == 1:
                    invoice_vals['partner_shipping_id'] = addresses.id
                invoice_vals['invoice_line_ids'] = lines
                invoice = contract.env['account.invoice'].create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
        if single_lines:
            for line in single_lines:
                if invoicing_method == 'computed':
                    contract = contract.with_context(force_date=line.date_invoice_next)
                invoice_vals = contract._prepare_invoice(do_raise=False, intervention_id=False)
                if not invoice_vals:
                    continue
                lines = line._add_invoice_lines()
                if not lines:
                    continue
                if line.line_id.address_id:
                    invoice_vals['partner_shipping_id'] = line.line_id.address_id.id
                invoice_vals['invoice_line_ids'] = lines
                invoice = contract.env['account.invoice'].create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
        return invoices

    def _handle_multiple_invoices_from_line(self, lines):
        date_stop = self.invoicing_period
        added_lines = []
        for line in lines:
            last_invoice_date = line.next_date
            next_date = self.date_from_line(line, last_invoice_date)
            while next_date and next_date <= date_stop:
                new_lines = line._add_invoice_lines()
                for nl in new_lines:
                    nl[2]['of_contract_supposed_date'] = next_date
                added_lines += new_lines
                next_date = self.date_from_line(line, next_date)
        return added_lines

    def date_from_line(self, line, last_invoice_date):
        frequency_type = line.frequency_type
        next_date = False
        if frequency_type == 'date':
            interventions = line.intervention_ids\
                                .filtered(lambda i: i.state == 'done' and i.date_date > last_invoice_date)
            if interventions:
                next_date = interventions.sorted('date_date')[0].date_date
                if line.recurring_invoicing_payment_id.code == 'post-paid':
                    # On se place au dernier jour du mois
                    base_date = fields.Date.from_string(next_date)
                    next_date = base_date + relativedelta(months=1, day=1, days=-1)
        else:
            invoice_lines = line.invoice_line_ids.filtered(lambda l: l.invoice_id.state != 'cancel')
            if not invoice_lines:
                base_date = fields.Date.from_string(last_invoice_date or line.date_contract_start)
                next_date = False
                if line.recurring_invoicing_payment_id.code == 'pre-paid':
                    if last_invoice_date:
                        if frequency_type == 'month':
                            next_date = base_date + relativedelta(months=1, day=1)
                        if frequency_type == 'trimester':
                            next_date = base_date + relativedelta(months=3, day=1)
                        if frequency_type == 'semester':
                            next_date = base_date + relativedelta(months=6, day=1)
                        if frequency_type == 'year':
                            next_date = base_date + relativedelta(years=1, month=1, day=1)
                    else:
                        if base_date.day != 1:
                            base_date = base_date + relativedelta(months=1)
                        next_date = base_date + relativedelta(day=1)
                else:
                    if frequency_type == 'month':
                        next_date = base_date + relativedelta(months=1, day=1, days=-1)
                    if frequency_type == 'trimester':
                        next_date = base_date + relativedelta(months=3, day=1, days=-1)
                    if frequency_type == 'semester':
                        next_date = base_date + relativedelta(months=6, day=1, days=-1)
                    if frequency_type == 'year':
                        next_date = base_date + relativedelta(years=1, month=1, day=1, days=-1)
            elif last_invoice_date:
                end = fields.Date.from_string(line.date_contract_end)
                freq_type = line.frequency_type
                if freq_type == 'month':
                    next_date = fields.Date.from_string(last_invoice_date) + relativedelta(months=1)
                    if line.recurring_invoicing_payment_id.code == 'pre-paid':
                        next_date = next_date + relativedelta(day=1)
                    else:
                        next_date = next_date + relativedelta(months=1, day=1, days=-1)
                    if not end or end > next_date:
                        line.next_date_date = next_date
                elif freq_type == 'trimester':
                    next_date = fields.Date.from_string(last_invoice_date) + relativedelta(months=3)
                    if line.recurring_invoicing_payment_id.code == 'pre-paid':
                        next_date = next_date + relativedelta(day=1)
                    else:
                        next_date = next_date + relativedelta(months=1, day=1, days=-1)
                    if not end or end > next_date:
                        line.next_date_date = next_date
                elif freq_type == 'semester':
                    next_date = fields.Date.from_string(last_invoice_date) + relativedelta(months=6)
                    if line.recurring_invoicing_payment_id.code == 'pre-paid':
                        next_date = next_date + relativedelta(day=1)
                    else:
                        next_date = next_date + relativedelta(months=1, day=1, days=-1)
                    if not end or end > next_date:
                        line.next_date = next_date
                elif freq_type == 'year':
                    next_date = fields.Date.from_string(last_invoice_date) + relativedelta(years=1)
                    if line.recurring_invoicing_payment_id.code == 'pre-paid':
                        next_date = next_date + relativedelta(day=1)
                    else:
                        next_date = next_date + relativedelta(months=1, day=1, days=-1)
        if next_date and isinstance(next_date, datetime.date):
            next_date = fields.Date.to_string(next_date)
        return next_date


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


class OFContractInvoicingExceptionWizard(models.TransientModel):
    _name ='of.contract.invoicing.exception.wizard'

    wizard_id = fields.Many2one(comodel_name='of.contract.invoicing.wizard', string="wizard", ondelete='cascade')
    contract_exception_id = fields.Many2one(
        comodel_name='of.contract.product.exception', string=u"Exception de facturation")
    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string=u"Ligne de contrat", related='contract_exception_id.line_id')
    selected = fields.Boolean(string=u"À facturer")
    line_code = fields.Char(string=u"Code", related='contract_line_id.code_de_ligne', readonly=True)
    line_address_id = fields.Many2one(
        string=u"Adresse d'intervention", related='contract_line_id.address_id', readonly=True)
    line_address_zip = fields.Char(string=u"CP", related='contract_line_id.address_zip', readonly=True)
    line_address_city = fields.Char(string=u"Ville", related='contract_line_id.address_city', readonly=True)
    line_supplier_id = fields.Many2one(
        comodel_name='res.partner', string=u"Prestataire", related='contract_line_id.supplier_id', readonly=True)
    exception_date_invoice_next = fields.Date(
        string=u"Date de facturation prévisionnelle", related='contract_exception_id.date_invoice_next')
    exception_amount_total = fields.Float(
        string=u"Montant de la prochaine exception", related='contract_exception_id.amount_total')
    exception_internal_note = fields.Text(string=u"Notes de l'exception", related='contract_exception_id.internal_note')
