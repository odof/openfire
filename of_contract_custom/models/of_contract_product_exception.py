# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFContractProductException(models.Model):
    _name = 'of.contract.product.exception'
    _order = 'state, date_invoice_next'

    line_id = fields.Many2one(comodel_name='of.contract.line', string=u"Ligne de contrat", required=True)
    date_invoice_next = fields.Date(string=u"Date de facturation prévisionnelle", required=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", required=True)
    name = fields.Char(string=u"Description", required=True)
    qty = fields.Float(string=u"Qté", default=1.0)
    qty_invoiced = fields.Float(string=u"Qté facturée")
    qty_to_invoice = fields.Float(string=u"Qté à facturer", compute='_compute_state_qty', store=True)
    amount_total = fields.Float(string=u"Montant total", compute='_compute_amount')
    price_unit = fields.Float(string=u"Prix unitaire")
    purchase_price = fields.Float(string=u"Coût")
    tax_ids = fields.Many2many(comodel_name='account.tax', string=u"Taxes")
    state = fields.Selection(selection=
        [
            ('1-to_invoice', u"À facturer"),
            ('2-invoiced', u"Facturé"),
        ], string=u"État", compute='_compute_state_qty', store=True)
    internal_note = fields.Text(string=u"Note interne")

    @api.depends('qty', 'qty_invoiced')
    def _compute_state_qty(self):
        for record in self:
            qty_to_invoice = record.qty - record.qty_invoiced
            record.qty_to_invoice = qty_to_invoice
            record.state = not qty_to_invoice and '2-invoiced' or '1-to_invoice'

    @api.depends('qty', 'price_unit', 'tax_ids', 'qty_invoiced', 'product_id', 'purchase_price',
                 'line_id.address_id', 'line_id.company_currency_id')
    def _compute_amount(self):
        for record in self:
            price = record.price_unit
            currency = record.line_id.company_currency_id
            qty_to_invoice = record.qty - record.qty_invoiced
            taxes = record.tax_ids.compute_all(price, currency, qty_to_invoice, product=record.product_id,
                                               partner=record.line_id.address_id)
            record.amount_total = taxes['total_included']

    @api.multi
    def _compute_tax_id(self):
        """ Calcul des taxes pour la ligne d'article """
        for record in self:
            fpos = record.line_id.fiscal_position_id or \
                   record.line_id.partner_id.property_account_position_id
            taxes = record.line_id.company_id._of_filter_taxes(record.product_id.taxes_id)
            record.tax_ids = fpos.map_tax(taxes, record.product_id, record.line_id.address_id) if fpos else taxes

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            product = self.product_id
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
            self.price_unit = product.list_price
            self.purchase_price = product.get_cost()
            self._compute_tax_id()

    @api.multi
    def _prepare_invoice_line(self):
        """ Renvoi un dictionnaire de valeur pour la facturation de l'article """
        self.ensure_one()
        invoice_line_new = self.env['account.invoice.line'].new({
            'product_id'   : self.product_id.id,
            'name': self.name,
            })
        type = 'out_invoice'
        product = self.product_id
        fpos = self.line_id.fiscal_position_id
        company = self.line_id.contract_id.company_id
        account = self.env['account.invoice.line'].get_invoice_line_account(type, product, fpos, company)
        for tax in self.tax_ids:
            account = tax.map_account(account)
        invoice_line_new._onchange_product_id()
        invoice_line_vals = invoice_line_new._convert_to_write(invoice_line_new._cache)
        name = u"%s" % (self.name or '')
        name += u"\n%s%s" % (self.line_id.address_id.name or u'',
                             self.line_id.partner_code_magasin and
                             (u", Magasin n°%s" % self.line_id.partner_code_magasin) or u'')
        invoice_line_vals.update({
            'quantity': self.qty_to_invoice,
            'uom_id': self.product_id.uom_id.id,
            'invoice_line_tax_ids': [(6, 0, [tax.id for tax in self.tax_ids])],
            'name': name,
            'price_unit': self.price_unit,
            'account_id': account.id,
        })
        self.write({'qty_invoiced': self.qty})
        return invoice_line_vals

    @api.multi
    def _add_invoice_lines(self):
        """
        Récupère un dictionnaire de valeurs pour chaque ligne de produit et créer une ligne de facture par article
        """
        lines = []
        for record in self:
            invoice_line_vals = record._prepare_invoice_line()
            lines.append((0, 0, invoice_line_vals))
        return lines
