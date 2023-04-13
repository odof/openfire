# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_payment_schedule_ids = fields.One2many(
        comodel_name='of.sale.payment.schedule', inverse_name='order_id', string="Payment schedule")

    @api.onchange('order_line')
    def _onchange_order_line(self):
        self.of_recompute_last_payment_schedule()

    def _of_compute_payment_schedule(self):
        self.ensure_one()
        if not self.payment_term_id:
            return False

        # Aujourd'hui, dans les lignes de contitions de règlement, on n'a
        #   ni la distinction entre date de facture et date de commande
        #   ni le libellé (qui était ajouté dans of_account en v10)
        # :todo: Améliorer le libellé et la date affichés

        date_ref = fields.Date.to_string(fields.Date.today())
        payment_terms = self.payment_term_id._compute_terms(
            date_ref=date_ref,
            currency=self.currency_id,
            company=self.company_id,
            tax_amount=self.amount_tax,
            tax_amount_currency=self.amount_tax,
            untaxed_amount=self.amount_untaxed,
            untaxed_amount_currency=self.amount_untaxed,
            sign=1)

        amount_total = self.amount_total
        pct_left = 100.0
        pct = 0
        result = [(5, )]
        for i, line in enumerate(payment_terms):
            pct_left -= pct
            amount = line['company_amount']
            pct = round(100 * amount / amount_total, 2) if amount_total else 0

            line_vals = {
                'name': _("Payment #%s") % i,
                'percent': pct,
                'amount': amount,
                'date': line['date'],
            }
            result.append((0, 0, line_vals))
        if len(result) > 1:
            result[-1][2]['percent'] = pct_left
        return result

    @api.onchange('payment_term_id')
    def _onchange_payment_term_id(self):
        if self.payment_term_id:
            self.of_payment_schedule_ids = self._of_compute_payment_schedule()

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        self._onchange_payment_term_id()

    # :todo: Calcul des dates de l'échéancier à décommenter et retravailler quand on saura comment on les gère
    # def of_update_payment_schedule_dates(self):
    #     for order in self:
    #         if not order.payment_term_id:
    #             continue
    #
    #         date_invoice = order.invoice_status == 'invoiced' and order.invoice_ids and \
    #             order.invoice_ids[0].date_invoice or False
    #         dates = {
    #             'order': order.confirmation_date,
    #             'invoice': date_invoice,
    #             'default': False,
    #         }
    #         force_dates = [echeance.date for echeance in order.of_echeance_line_ids]
    #         echeances = order.payment_term_id.compute(order.amount_total, dates=dates, force_dates=force_dates)[0]
    #
    #         if len(echeances) != len(order.of_echeance_line_ids):
    #             continue
    #
    #         for echeance, ech_calc in itertools.izip(order.of_echeance_line_ids, echeances):
    #             if ech_calc[0] and not echeance.date:
    #                 echeance.date = ech_calc[0]

    # def action_confirm(self):
    #     res = super(SaleOrder, self).action_confirm()
    #     self.of_update_dates_echeancier()
    #     return res

    def of_recompute_last_payment_schedule(self):
        for order in self:
            if not order.of_payment_schedule_ids:
                continue

            percent = 100.0
            amount = order.amount_total
            for payment in order.of_payment_schedule_ids:
                if payment.is_last:
                    payment.write({
                        'percent': percent,
                        'amount': amount,
                    })
                else:
                    percent -= payment.percent
                    amount -= payment.amount

    def pdf_payment_schedule(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_payment_schedule')

    def write(self, vals):
        def payment_schedule_needs_recompute(order):
            return order.of_payment_schedule_ids \
                and float_compare(
                    order.amount_total,
                    sum(order.of_payment_schedule_ids.mapped('amount')),
                    precision_rounding=.01)
        res = super().write(vals)
        # Recalcul de la dernière échéance si besoin
        self.filtered(payment_schedule_needs_recompute).of_recompute_last_payment_schedule()
        return res
