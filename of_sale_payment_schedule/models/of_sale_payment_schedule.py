# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.tools import float_compare


class OFSalePaymenSchedule(models.Model):
    _name = 'of.sale.payment.schedule'
    _order = 'order_id, sequence, id'

    name = fields.Char(required=True, default="Échéance")
    order_id = fields.Many2one(comodel_name='sale.order', string="Sale order")
    currency_id = fields.Many2one(related='order_id.currency_id', readonly=True)
    amount = fields.Monetary(currency_field='currency_id')
    percent = fields.Float(string="Percentage", digits='Product Price')
    # :todo: rename depuis l'ancien nom : last
    is_last = fields.Boolean(string="Last payment", compute='_compute_is_last')
    sequence = fields.Integer()
    date = fields.Date()

    def _compute_is_last(self):
        for order in self.mapped('order_id'):
            for payment in order.of_payment_schedule_ids:
                payment.is_last = payment == order.of_payment_schedule_ids[-1]

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
