# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFOutlayAnalysisEntry(models.Model):
    _name = 'of.outlay.analysis.entry'
    _description = u"Entrées manuelles pour les débours"
    _order = 'date, id'

    @api.model
    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    analysis_id = fields.Many2one(comodel_name='of.outlay.analysis', string=u"Analyse de débours", required=True)
    type = fields.Selection(selection=[('income', u"Produit"), ('expense', u"Charge")], required=True)
    line_type = fields.Selection(
        selection=[('init', u"Initial"), ('compl', u"Complémentaire")], string=u"Budget", required=True
    )
    date = fields.Date()
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article")
    name = fields.Char(string=u"Libellé")
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string=u"Compte analytique")
    analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")
    qty = fields.Float(string=u"Quantité", default=1.0)
    price_unit = fields.Monetary(string=u"Prix unitaire", currency_field='currency_id')
    price_subtotal = fields.Monetary(
        string=u"Prix total", currency_field='currency_id', compute='_compute_price_subtotal', store=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='analysis_id.currency_id', string=u"Devise", readonly=True
    )

    @api.depends('qty', 'price_unit')
    def _compute_price_subtotal(self):
        for entry in self:
            entry.price_subtotal = entry.currency_id.round(entry.price_unit * entry.qty)
