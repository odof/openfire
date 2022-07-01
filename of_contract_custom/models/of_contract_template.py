# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta


class OFContractTemplate(models.Model):
    _name = 'of.contract.template'
    _inherit = 'of.documents.joints'

    @api.model
    def get_ctype_selection(self):
        return self.env['of.contract'].get_ctype_selection()

    @api.model
    def get_ctype_default(self):
        return self.env['of.contract'].get_ctype_default()

    name = fields.Char(string=u"Nom du modèle", required=True)
    jour_debut = fields.Integer(string=u"Jour de début")
    mois_id = fields.Many2one(comodel_name='of.mois', string=u"Mois de début")
    frequency = fields.Selection(selection=[
        ('date', u"À la prestation"),
        ('days', "Jour"),
        ('weeks', "Semaine"),
        ('months', "Mois"),
        ('trimester', "Trimestre"),
        ('semester', "Semestre"),
        ('years', u"Année"),
        ], string=u"Fréquence de facturation")
    frequency_amount = fields.Integer(string="Amount")
    renewal = fields.Boolean(string="Renouveler")
    use_index = fields.Boolean(string="Indexer")
    grouped = fields.Boolean(string="Regrouper la facturation")
    prorata = fields.Boolean(string="Prorata")
    contract_type = fields.Selection([
        ('simple', u'Simple'),
        ('advanced', u'Avancé'),
        ], string="Type de contrat", default='simple', required=True
    )
    journal_id = fields.Many2one(comodel_name='account.journal', string="Journal")
    property_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Position fiscale", company_dependent=True)
    payment_term_id = fields.Many2one(comodel_name='account.payment.term', string=u"Conditions de règlement")
    line_ids = fields.One2many(
        comodel_name='of.contract.line.template', inverse_name='template_id', string="Lignes", copy=True)
    ctype = fields.Selection(
        selection=lambda r: r.get_ctype_selection(), string="Type de contrat", default=lambda r: r.get_ctype_default(),
        required=True
    )
    commentaires = fields.Text(string="Commentaires")

    def template_to_record_vals(self):
        self.ensure_one()
        date = datetime.today() + relativedelta(day=self.jour_debut, month=self.mois_id.numero)
        return {
            'date_start': fields.Date.to_string(date),
            'frequency': self.frequency,
            'frequency_amount': self.frequency_amount,
            'renewal': self.renewal,
            'use_index': self.use_index,
            'grouped': self.grouped,
            'prorata': self.prorata,
            'contract_type': self.contract_type,
            'journal_id': self.journal_id.id,
            'fiscal_position_id': self.property_fiscal_position_id.id,
            'payment_term_id': self.payment_term_id.id,
            'ctype': self.ctype,
            'commentaires': self.commentaires,
            'date_end': not self.renewal and fields.Date.to_string(date + relativedelta(years=1)),
            'line_ids': [(0, 0, line.template_to_record_vals()) for line in self.line_ids],
        }


class OFContractLineTemplate(models.Model):
    _name = 'of.contract.line.template'
    _inherit = 'of.planning.plannification'

    template_id = fields.Many2one(comodel_name='of.contract.template', string=u"Modèle")
    name = fields.Char(string=u"Nom du modèle", required=True)
    ctype = fields.Selection(related='template_id.ctype')
    jour_debut = fields.Integer(string=u"Jour de début", required=True)
    mois_id = fields.Many2one(comodel_name='of.mois', string=u"Mois de début")
    frequency = fields.Selection(selection=[
        ('date', u"À la prestation"),
        ('days', "Jour"),
        ('weeks', "Semaine"),
        ('months', "Mois"),
        ('trimester', "Trimestre"),
        ('semester', "Semestre"),
        ('years', u"Année"),
        ], string=u"Fréquence de facturation")
    frequency_amount = fields.Integer(string="Amount")
    contract_type = fields.Selection(related="template_id.contract_type", readonly=True)
    grouped = fields.Boolean(string="Regrouper la facturation")
    property_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Position fiscale", company_dependent=True)
    tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche")
    notes = fields.Text(strong="Notes")
    product_ids = fields.One2many(
        comodel_name='of.contract.product.template', inverse_name='template_line_id', string=u"Articles à facturer")

    def template_to_record_vals(self):
        self.ensure_one()
        date = fields.Date.to_string(datetime.today() + relativedelta(day=self.jour_debut, month=self.mois_id.numero))
        return {
            'date_start': date,
            'frequency': self.frequency,
            'frequency_amount': self.frequency_amount,
            'grouped': self.grouped,
            'fiscal_position_id': self.property_fiscal_position_id.id,
            'tache_id': self.tache_id.id,
            'notes': self.notes,
            'first_invoicing': date,
            'contract_product_ids': [(0, 0, product_line.template_to_record_vals())
                                     for product_line in self.product_ids],
            'interv_frequency_nbr': self.interv_frequency_nbr,
            'interv_frequency': self.interv_frequency,
            'mois_reference_ids': [(4, mois.id) for mois in self.mois_reference_ids],
        }


class OFContractProductTemplate(models.Model):
    _name = 'of.contract.product.template'

    template_line_id = fields.Many2one(comodel_name='of.contract.line.template', string=u"Ligne de modèle")
    product_id = fields.Many2one(comodel_name='product.product', string="article")
    price_unit = fields.Float(string="Prix unitaire")
    purchase_price = fields.Float(string=u"Coût")
    quantity = fields.Float(string=u"Qté", default=1.0)
    uom_id = fields.Many2one('product.uom', string=u'Unité de mesure')
    amount_subtotal = fields.Float(
        string="Sous-total", compute='_compute_amount', digits=dp.get_precision('Account'), store=True)
    amount_taxes = fields.Float(
        string="Taxes ", compute='_compute_amount', store=True)
    amount_total = fields.Float(
        string="Prochain Total", compute='_compute_amount', store=True)
    discount = fields.Float(
        string='Remise (%)', digits=dp.get_precision('Discount'), help=u'Remise appliquée pour les factures')
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'sale')], copy=True)

    @api.depends('quantity', 'price_unit', 'tax_ids', 'purchase_price', 'product_id')
    def _compute_amount(self):
        """ Calcul des montants pour la ligne d'article """
        # c_product pour contract_product
        for c_product in self:
            company_currency = self.env.user.company_id.currency_id
            price = c_product.price_unit * (1 - (c_product.discount or 0.0) / 100.0)
            taxes = c_product.tax_ids.compute_all(price, company_currency, c_product.quantity,
                                                  product=c_product.product_id)
            c_product.amount_taxes = taxes['total_included'] - taxes['total_excluded']
            c_product.amount_total = taxes['total_included']
            c_product.amount_subtotal = taxes['total_excluded']

    @api.multi
    def _compute_tax_id(self):
        """ Calcul des taxes pour la ligne d'article """
        for c_product in self:
            fpos = c_product.template_line_id.property_fiscal_position_id
            taxes = self.env.user.company_id._of_filter_taxes(c_product.product_id.taxes_id)
            c_product.tax_ids = fpos.map_tax(taxes, c_product.product_id, False) \
                if fpos else taxes

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            product = self.product_id
            self.price_unit = product.list_price
            self.purchase_price = product.standard_price
            self.uom_id = product.uom_id
            self._compute_tax_id()

    def template_to_record_vals(self):
        self.ensure_one()
        name = self.product_id.name_get()[0][1]
        if self.product_id.description_sale:
            name += '\n' + self.product_id.description_sale
        return {
            'name': name,
            'product_id': self.product_id.id,
            'price_unit': self.price_unit,
            'purchase_price': self.purchase_price,
            'quantity': self.quantity,
            'uom_id': self.uom_id.id,
            'discount': self.discount,
            'tax_ids': [(4, tax.id) for tax in self.tax_ids],
        }
