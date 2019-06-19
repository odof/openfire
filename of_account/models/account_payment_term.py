# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, exceptions, _
from odoo.tools.float_utils import float_is_zero, float_round
import odoo.addons.decimal_precision as dp
import calendar


class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    option = fields.Selection([
            ('day_after_invoice_date', u'À partir de la date de référence'),
            ('fix_day_following_month', u'À partir de la fin du mois'),
            ('last_day_following_month', 'Last day of following month'),
            ('last_day_current_month', 'Last day of current month'),
        ],
        default='day_after_invoice_date', required=True, string='Mode de calcul'
        )
    name = fields.Char(string=u"Libellé", required=True, default=u"Échéance")
    of_option_date = fields.Selection(
        '_get_of_option_date', string="Date de référence", required=True, default='invoice')
    of_amount_round = fields.Float(
        string='Arrondi du montant',
        digits=dp.get_precision('Account'),
        help=u"Arrondit le montant à un multiple de cette valeur")
    of_months = fields.Integer(string='Nombre de mois')
    of_weeks = fields.Integer(string='Nombre de semaines')
    of_payment_days = fields.Char(
        string='Jours du mois',
        help="Liste des jours du mois valides pour les paiements, séparés par des virgules (,), 'espaces blancs ( ) "
             "ou tirets pour des périodes (-).")

    @api.model
    def _get_of_option_date(self):
        return [('invoice', 'Date de facture'), ('previous', u'Échéance précédente')]

    @api.model
    def of_decode_payment_days(self, days_char):
        # les jours sont séparés par des ' ' ou ','. Des '-' indiquent des périodes.
        days_char = days_char.replace(',', ' ')
        days = []
        for day_char in days_char.split():
            if '-' in day_char:
                d = [int(d) for d in day_char.split('-')]
                days += range(d[0], d[-1]+1)
            else:
                days.append(int(day_char))
        days.sort()
        return days

    @api.multi
    def of_apply_payment_days(self, date):
        """Calculate the new date with days of payments"""
        self.ensure_one()
        if self.of_payment_days:
            payment_days = self.of_decode_payment_days(self.of_payment_days)
            if payment_days:
                new_date = None
                days_in_month = calendar.monthrange(date.year, date.month)[1]

                months = 0
                for day in payment_days:
                    if date.day <= day:
                        break
                else:
                    day = payment_days[0]
                    months = 1
                if day > days_in_month:
                    day = days_in_month
                new_date = date + relativedelta(day=day, months=months)
                return new_date
        return date

    @api.multi
    def of_compute_line_date(self, dates):
        self.ensure_one()
        next_date = dates[self.of_option_date]
        if not next_date:
            return False

        if self.option == 'day_after_invoice_date':
            next_date += relativedelta(days=self.days,
                                       weeks=self.of_weeks,
                                       months=self.of_months)
        elif self.option == 'fix_day_following_month':
            # Getting 1st of next month
            next_first_date = next_date + relativedelta(day=1, months=1)
            next_date = next_first_date + relativedelta(days=self.days - 1,
                                                        weeks=self.of_weeks,
                                                        months=self.of_months)
        elif self.option == 'last_day_following_month':
            # Getting last day of next month
            next_date += relativedelta(day=31, months=1)
        elif self.option == 'last_day_current_month':
            # Getting last day of next month
            next_date += relativedelta(day=31, months=0)
        next_date = self.of_apply_payment_days(next_date)
        return next_date

    @api.multi
    def of_compute_line_amount(self, total_amount, remaining_amount, precision_digits):
        """Compute the amount for a payment term line.
        In case of procent computation, use the payment
        term line rounding if defined

            :param total_amount: total balance to pay
            :param remaining_amount: total amount minus sum of previous lines
                computed amount
            :returns: computed amount for this line
        """
        self.ensure_one()
        amount = None
        if self.value == 'fixed':
            amount = self.value_amount * (total_amount < 0 and -1 or 1)
        elif self.value == 'percent':
            amount = total_amount * (self.value_amount / 100.0)
            if self.of_amount_round:
                amount = float_round(amount, precision_rounding=self.of_amount_round)
        elif self.value == 'balance':
            amount = remaining_amount
        return amount and float_round(amount, precision_digits=precision_digits)

    @api.one
    @api.constrains('of_payment_days')
    def _check_of_payment_days(self):
        if not self.of_payment_days:
            return
        try:
            payment_days = self.of_decode_payment_days(self.of_payment_days)
            error = payment_days and (payment_days[0] <= 0 or payment_days[-1] > 31)
        except Exception:
            error = True
        if error:
            raise exceptions.Warning(_("Le format des jours de paiement n'est pas valide."))

class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    @api.one
    def compute(self, value, date_ref=False, dates={}, force_dates=False):
        """
        @param date_ref: Date de facturation. Champ conservé pour compatibilité Odoo.
        @param dates: Dictionnaire des autres dates pouvant être utilisées.
            Peut contenir une valeur 'default' pour les dates manquantes, sans quoi la date courante sera utilisée.
        @param force_dates: Liste de valeurs (string de date ou False), dans l'ordre des lignes d'échéances.
            Si renseigné, doit avoir une valeur par ligne d'échéance dont le montant est différent de 0.
        """
        default = dates.get('default', fields.Date.today())
        dates = {
            date_field: fields.Date.from_string(dates.get(date_field) or default)
            for date_field in self.env['account.payment.term.line']._fields['of_option_date'].get_values(self.env)
        }
        if date_ref:
            dates['invoice'] = fields.Date.from_string(date_ref)

        amount = value
        result = []
        if self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        else:
            currency = self.env.user.company_id.currency_id
        prec = currency.decimal_places

        i = 0
        for line in self.line_ids:
            amt = line.of_compute_line_amount(value, amount, prec)

            if float_is_zero(amt, precision_rounding=prec):
                dates['previous'] = line.of_compute_line_date(dates)
            else:
                if force_dates and len(force_dates) > i and force_dates[i]:
                    dates['previous'] = fields.Date.from_string(force_dates[i])
                else:
                    dates['previous'] = line.of_compute_line_date(dates)
                i += 1
                result.append((fields.Date.to_string(dates['previous']), amt))
                amount -= amt
        amount = reduce(lambda x, y: x + y[1], result, 0.0)
        dist = round(value - amount, prec)
        if dist:
            last_date = result and result[-1][0] or fields.Date.today()
            result.append((last_date, dist))
        return result
