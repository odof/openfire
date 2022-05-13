# -*- coding: utf-8 -*-
import odoo.addons.decimal_precision as dp
from odoo import models, fields, api
from odoo.tools import float_compare


class OFSaleEcheance(models.Model):
    _name = "of.sale.echeance"
    _order = "order_id, sequence, id"

    name = fields.Char(string="Nom", required=True, default=u"Échéance")
    order_id = fields.Many2one("sale.order", string="Commande")
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)  # TODO ADAPT SALE
    amount = fields.Monetary(string="Montant", currency_field='currency_id')
    percent = fields.Float(string=u"Pourcentage", digits=dp.get_precision('Product Price'))
    last = fields.Boolean(string=u"Dernière Échéance", compute="_compute_last")

    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of payment term lines.")
    date = fields.Date(string='Date')

    @api.multi
    def _compute_last(self):
        for order in self.mapped('order_id'):
            for echeance in order.of_echeance_line_ids:
                echeance.last = echeance == order.of_echeance_line_ids[-1]

    @api.onchange("amount")
    def _onchange_amount(self):
        """Met à jour le pourcentage en fonction du montant"""
        order_amount = self._context.get('order_amount', self.order_id.amount_total)
        # Test: si le nouveau montant est calculé depuis le pourcentage, on ne le recalcule pas
        test_amount = order_amount * self.percent / 100
        if float_compare(self.amount, test_amount, precision_rounding=.01):
            self.percent = self.amount * 100 / order_amount if order_amount else 0

    @api.onchange("percent")
    def _onchange_percent(self):
        """Met à jour le montant en fonction du pourcentage"""
        order_amount = self._context.get('order_amount', self.order_id.amount_total)
        # Test: si le nouveau pourcentage est calculé depuis le montant, on ne le recalcule pas
        test_percent = self.amount * 100 / order_amount if order_amount else 0
        if float_compare(self.percent, test_percent, precision_rounding=.01):
            self.amount = order_amount * self.percent / 100
