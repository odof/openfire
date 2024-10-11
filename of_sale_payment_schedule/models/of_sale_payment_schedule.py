# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools import float_compare


class OFSalePaymenSchedule(models.Model):
    _name = "of.sale.payment.schedule"
    _description = "Sale Payment Schedule"
    _order = "order_id, sequence, id"

    def _default_payment_schedule_name(self):
        return _("Due")

    name = fields.Char(required=True, default=lambda self: self._default_payment_schedule_name())
    order_id = fields.Many2one(comodel_name="sale.order", string="Sale order")
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    amount = fields.Monetary(currency_field="currency_id", compute="_compute_amount", readonly=False, store=True)
    percent = fields.Float(
        string="Percentage", digits="Product Price", compute="_compute_percent", readonly=False, store=True
    )
    # TODO: rename depuis l'ancien nom : last
    is_last = fields.Boolean(string="Last payment", compute="_compute_is_last")
    sequence = fields.Integer()
    date = fields.Date()

    def _compute_is_last(self):
        for order in self.mapped("order_id"):
            for payment in order.of_payment_schedule_ids:
                payment.is_last = payment == order.of_payment_schedule_ids[-1]

    @api.depends("amount")
    def _compute_percent(self):
        for payment in self:
            order_amount = payment._context.get("order_amount", payment.order_id.amount_total)
            test_amount = order_amount * payment.percent / 100
            if float_compare(payment.amount, test_amount, precision_rounding=0.01):
                payment.percent = payment.amount * 100 / order_amount if order_amount else 0

    @api.depends("percent")
    def _compute_amount(self):
        for payment in self:
            order_amount = payment._context.get("order_amount", payment.order_id.amount_total)
            test_percent = payment.amount * 100 / order_amount if order_amount else 0
            if float_compare(payment.percent, test_percent, precision_rounding=0.01):
                payment.amount = order_amount * payment.percent / 100
