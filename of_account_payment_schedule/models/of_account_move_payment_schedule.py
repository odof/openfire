# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools import float_compare


class OFAccountPaymentSchedule(models.Model):
    _name = 'of.account.move.payment.schedule'
    _description = "Account Payment Schedule"
    _order = 'move_id, sequence, id'

    def _default_payment_schedule_name(self):
        return _("Due")

    name = fields.Char(required=True, default=lambda self: self._default_payment_schedule_name())
    move_id = fields.Many2one(comodel_name='account.move', string="Invoice")
    currency_id = fields.Many2one(related='move_id.currency_id', readonly=True)
    amount = fields.Monetary(currency_field='currency_id', compute='_compute_amount', readonly=False, store=True)
    percent = fields.Float(
        string="Percentage", digits='Product Price', compute='_compute_percent', readonly=False, store=True
    )
    is_last = fields.Boolean(string="Last payment", compute='_compute_is_last')
    sequence = fields.Integer()
    date = fields.Date()

    def _compute_is_last(self):
        for move in self.mapped('move_id'):
            for payment in move.of_payment_schedule_ids:
                payment.is_last = payment == move.of_payment_schedule_ids[-1]

    @api.depends('amount')
    def _compute_percent(self):
        for payment in self:
            account_move_amount = payment._context.get('account_move_amount', payment.move_id.amount_total)
            test_amount = account_move_amount * payment.percent / 100
            if float_compare(payment.amount, test_amount, precision_rounding=0.01):
                payment.percent = payment.amount * 100 / account_move_amount if account_move_amount else 0

    @api.depends('percent')
    def _compute_amount(self):
        for payment in self:
            account_move_amount = payment._context.get('account_move_amount', payment.move_id.amount_total)
            test_percent = payment.amount * 100 / account_move_amount if account_move_amount else 0
            if float_compare(payment.percent, test_percent, precision_rounding=0.01):
                payment.amount = account_move_amount * payment.percent / 100
