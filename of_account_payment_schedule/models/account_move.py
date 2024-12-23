# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    of_payment_schedule_ids = fields.One2many(
        comodel_name="of.account.move.payment.schedule",
        inverse_name="move_id",
        string="Payment schedule",
        compute="_compute_of_payment_schedule_ids",
        store=True,
        readonly=False,
    )

    of_show_update_payment_schedule = fields.Boolean(
        string="Payment schedule needs to be updated", compute="_compute_of_show_update_payment_schedule"
    )

    # ----------------------------------------------------------
    # Compute methods
    # ----------------------------------------------------------

    @api.depends("invoice_payment_term_id", "invoice_line_ids.price_total", "amount_total")
    def _compute_of_show_update_payment_schedule(self):
        for move in self:
            of_show_update_payment_schedule = False
            if move.state in ("draft", "posted") and (
                not move.of_payment_schedule_ids
                or move.of_payment_schedule_ids
                and move._get_payment_schedule_needs_recompute()
                # si la date d'échéance sur la facture n'est pas égale à celle de ligne d'échéance qui a value = balance
                or (move.invoice_date_due not in move.of_payment_schedule_ids.mapped("date"))
            ):
                of_show_update_payment_schedule = True
            move.of_show_update_payment_schedule = of_show_update_payment_schedule

    @api.depends("invoice_payment_term_id")
    def _compute_of_payment_schedule_ids(self):
        if self.invoice_payment_term_id:
            self.of_payment_schedule_ids = self._of_compute_payment_schedule()

    # ----------------------------------------------------------
    # Onchange methods
    # ----------------------------------------------------------

    @api.onchange("line_ids")
    def _onchange_line_ids(self):
        self.of_recompute_last_payment_schedule()

    @api.onchange("amount_total")
    def _onchange_amount_total(self):
        self._compute_of_payment_schedule_ids()

    # ----------------------------------------------------------
    # ORM methods
    # ----------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        # Recalcul de la dernière échéance si besoin
        if move_needs_recompute := self._get_payment_schedule_needs_recompute():
            move_needs_recompute.of_recompute_last_payment_schedule()
        return res

    def copy(self, default=None):
        res = super().copy(default=default)
        res._compute_of_payment_schedule_ids()
        return res

    # ----------------------------------------------------------
    # Action methods
    # ----------------------------------------------------------

    def action_post(self):
        res = super().action_post()
        self.of_update_payment_schedule_dates()
        return res

    # ----------------------------------------------------------
    # Business methods
    # ----------------------------------------------------------

    def _of_compute_payment_schedule(self):
        self.ensure_one()
        if not self.invoice_payment_term_id or not self.currency_id:
            return False
        date_ref = fields.Date.to_string(fields.Date.today())
        payment_terms = self.invoice_payment_term_id._compute_terms(
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
            pct_left -= pct if self.amount_untaxed > 0 else line["value_amount"]
            amount = line["company_amount"]
            pct = round(100 * amount / amount_total, 2) if amount_total else 0
            line_vals = {
                "name": line["name"],
                "percent": pct if self.amount_untaxed > 0 else line["value_amount"],
                "amount": amount,
                "date": line["date"],
                "value": line["value"],
            }
            # Mettre à jour la date de l'échéance dans le tableau d'échéance si on a la date d'échéance de facture
            # n'est pas la meme de celui de tableau d'échéance (pour les valeurs solde : value = balance)
            if (not self.invoice_date or self.invoice_date != fields.Date.today()) and (
                self.invoice_date_due not in self.of_payment_schedule_ids.mapped("date")
            ):
                if line_vals["value"] == "balance":
                    line_vals["date"] = self.invoice_date_due

            result.append(Command.create(line_vals))
        if len(result) > 1:
            result[-1][2]["percent"] = pct_left
        return result

    def of_update_payment_schedule_dates(self):
        for move in self:
            if not move.invoice_payment_term_id:
                continue

            date_ref = fields.Date.to_string(fields.Date.today())
            payment_terms = self.invoice_payment_term_id._compute_terms(
                date_ref=date_ref,
                currency=self.currency_id,
                company=self.company_id,
                tax_amount=self.amount_tax,
                tax_amount_currency=self.amount_tax,
                untaxed_amount=self.amount_untaxed,
                untaxed_amount_currency=self.amount_untaxed,
                sign=1,
            )
            if len(payment_terms) != len(move.of_payment_schedule_ids):
                continue

            for payment_schedule, payment_term in zip(move.of_payment_schedule_ids, payment_terms):
                if payment_term["date"] and not payment_schedule.date or payment_term["date"] != payment_schedule.date:
                    payment_schedule.date = payment_term["date"]

    def of_recompute_last_payment_schedule(self):
        for move in self:
            # Only draft and posted moves can have their payment schedule recomputed totally
            if move.state in ("draft", "posted") and move._get_payment_schedule_needs_recompute():
                move.of_payment_schedule_ids = move._of_compute_payment_schedule()
                continue

            percent = 100.0
            amount = move.amount_total
            for payment in move.of_payment_schedule_ids:
                if payment.is_last:
                    payment.write(
                        {
                            "percent": percent,
                            "amount": amount,
                        }
                    )
                else:
                    percent -= payment.percent
                    amount -= payment.amount

    def action_button_update_payment_schedule(self):
        self.ensure_one()
        self.of_payment_schedule_ids = self._of_compute_payment_schedule()

    def _get_payment_schedule_needs_recompute(self):
        """Returns the invoices that need to have their payment schedule recomputed"""

        def filter_needs_recompute(move):
            return (
                move.invoice_payment_term_id
                and not move.of_payment_schedule_ids
                or move.of_payment_schedule_ids
                and float_compare(
                    move.amount_total, sum(move.of_payment_schedule_ids.mapped("amount")), precision_rounding=0.01
                )
            )

        return self.filtered(filter_needs_recompute)

    # ----------------------------------------------------------
    # Helper methods for QWeb reports
    # ----------------------------------------------------------

    def pdf_invoice_payment_schedule(self):
        return self.company_id.of_pdf_invoice_payment_schedule
