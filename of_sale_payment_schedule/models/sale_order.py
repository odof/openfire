# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_payment_schedule_ids = fields.One2many(
        comodel_name='of.sale.payment.schedule',
        inverse_name='order_id',
        string="Payment schedule",
        compute='_compute_of_payment_schedule_ids',
        store=True,
        readonly=False,
    )
    of_show_update_payment_schedule = fields.Boolean(
        string="Payment schedule needs to be updated", compute='_compute_of_show_update_payment_schedule'
    )

    @api.depends('payment_term_id', 'order_line.price_total', 'amount_total')
    def _compute_of_show_update_payment_schedule(self):
        for order in self:
            of_show_update_payment_schedule = False
            if order.state in ('draft', 'sent') and (
                not order.of_payment_schedule_ids
                or order.of_payment_schedule_ids
                and order._get_payment_schedule_needs_recompute()
            ):
                of_show_update_payment_schedule = True
            order.of_show_update_payment_schedule = of_show_update_payment_schedule

    @api.onchange('order_line')
    def _onchange_order_line(self):
        self.of_recompute_last_payment_schedule()

    def _of_compute_payment_schedule(self):
        self.ensure_one()
        if not self.payment_term_id or not self.currency_id:
            return False

        # Aujourd'hui, dans les lignes de contitions de règlement, on n'a
        #   ni la distinction entre date de facture et date de commande
        #   ni le libellé (qui était ajouté dans of_account en v10)
        # TODO: Améliorer le libellé et la date affichés

        date_ref = fields.Date.to_string(fields.Date.today())
        payment_terms = self.payment_term_id._compute_terms(
            date_ref=date_ref,
            currency=self.currency_id,
            company=self.company_id,
            tax_amount=self.amount_tax,
            tax_amount_currency=self.amount_tax,
            untaxed_amount=self.amount_untaxed,
            untaxed_amount_currency=self.amount_untaxed,
            sign=1,
        )

        amount_total = self.amount_total
        pct_left = 100.0
        pct = 0
        result = [Command.clear()]
        for i, line in enumerate(payment_terms, 1):
            pct_left -= pct
            amount = line['company_amount']
            pct = round(100 * amount / amount_total, 2) if amount_total else 0

            line_vals = {
                'name': _("Payment #%s") % i,
                'percent': pct,
                'amount': amount,
                'date': line['date'],
            }
            result.append(Command.create(line_vals))
        if len(result) > 1:
            result[-1][2]['percent'] = pct_left
        return result

    @api.depends('payment_term_id')
    def _compute_of_payment_schedule_ids(self):
        if self.payment_term_id:
            self.of_payment_schedule_ids = self._of_compute_payment_schedule()

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        self._compute_of_payment_schedule_ids()

    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # TODO Calcul des dates de l'échéancier à décommenter et retravailler quand on saura comment on les gère
    # def of_update_payment_schedule_dates(self):
    #     for order in self:
    #         if not order.payment_term_id:
    #             continue

    #         invoice_date = order.invoice_status == 'invoiced' and order.invoice_ids and \
    #             order.invoice_ids[0].invoice_date or False
    #         dates = {
    #             'order': order.date_order,
    #             'invoice': invoice_date,
    #             'default': False,
    #         }
    #         force_dates = [echeance.date for echeance in order.of_payment_schedule_ids]
    #         milestones = order.payment_term_id.compute(order.amount_total, dates=dates, force_dates=force_dates)[0]

    #         if len(milestones) != len(order.of_payment_schedule_ids):
    #             continue

    #         for payment_schedule, milestone in zip(order.of_payment_schedule_ids, milestones):
    #             if milestone[0] and not payment_schedule.date:
    #                 payment_schedule.date = milestone[0]

    # def action_confirm(self):
    #     res = super().action_confirm()
    #     self.of_update_payment_schedule_dates()
    #     return res
    # TODO: End of uncomment me

    def of_recompute_last_payment_schedule(self):
        for order in self:
            if not order.of_payment_schedule_ids:
                self.of_payment_schedule_ids = self._of_compute_payment_schedule()
                continue

            percent = 100.0
            amount = order.amount_total
            for payment in order.of_payment_schedule_ids:
                if payment.is_last:
                    payment.write(
                        {
                            'percent': percent,
                            'amount': amount,
                        }
                    )
                else:
                    percent -= payment.percent
                    amount -= payment.amount

    def action_button_update_payment_schedule(self):
        self.ensure_one()
        self.of_payment_schedule_ids = self._of_compute_payment_schedule()

    def pdf_payment_schedule(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_payment_schedule')

    def _get_payment_schedule_needs_recompute(self):
        """Returns the orders that need to have their payment schedule recomputed"""

        def filter_needs_recompute(order):
            return (
                (order.payment_term_id and not order.of_payment_schedule_ids)
                or order.of_payment_schedule_ids
                and float_compare(
                    order.amount_total, sum(order.of_payment_schedule_ids.mapped('amount')), precision_rounding=0.01
                )
            )

        return self.filtered(filter_needs_recompute)

    def write(self, vals):
        res = super().write(vals)
        # Recalcul de la dernière échéance si besoin
        if order_needs_recompute := self._get_payment_schedule_needs_recompute():
            order_needs_recompute.of_recompute_last_payment_schedule()
        return res

    def copy(self, default=None):
        res = super().copy(default=default)
        res._onchange_payment_term_id()
        return res
