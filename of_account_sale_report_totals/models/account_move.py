# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    """Methods that are starts with `_of_report_` are used in the report template."""

    _inherit = 'account.move'

    # --------------------------------------------------------------------------
    # Reporting methods
    # --------------------------------------------------------------------------

    def _of_get_total_lines_by_group(self, invoices):
        """
        Returns the invoice lines, separated by the group in which they should be displayed.

        The groups are defined by the `of.invoice.report.total` object, allowing to move the rendering of the invoice
        lines under the total amount (TTC).

        Groups are displayed in their own order, followed by the lines in the order they appear in the invoice.

        Args:
            invoices (recordset): The set of invoices to use for generating the document.

        Returns:
            list: A list of tuples `(group, invoice lines)`.
                The first element is `(False, <Ungrouped Lines>)`.
                The second element is `(group_tax, <Tax Lines>)`.
                The third element is `(group_payment, <Payment Lines>)`.
        """

        self.ensure_one()
        group_obj = self.env['of.invoice.report.total.group']
        move_line_obj = self.env['account.move.line']

        lines = self.invoice_line_ids.sorted(  # Sort lines as they are sorted in the standard report
            key=lambda line: (-line.sequence, line.date, line.move_name, -line.id), reverse=True
        )
        products = lines.mapped('product_id')
        product_ids = products.ids
        categ_ids = products.mapped('categ_id').ids
        group_payments = group_obj.get_payments_group()
        group_taxes = group_obj.get_taxes_group()
        groups = group_obj.search(
            [
                ('is_affect_invoice', '=', True),
                '|',
                '|',
                ('id', 'in', (group_payments.id, group_taxes.id)),
                ('product_ids', 'in', product_ids),
                ('categ_ids', 'in', categ_ids),
            ]
        )

        result = []
        group_taxes_lines = move_line_obj

        # Payment group can absorb lines from other groups. It must be processed first.
        group_payment_lines = group_payments.filter_lines(lines, invoices - self)
        if group_payment_lines:
            lines -= group_payment_lines

        # Split lines into groups
        for group in groups:
            if group == group_payments:
                result.append((group, group_payment_lines))
            else:
                group_lines = group.filter_lines(lines)
                if group_lines or group == group_taxes:
                    result.append((group, group_lines))
                    lines -= group_lines
                if group == group_taxes:
                    group_taxes_lines = group_lines

        return (
            [(False, lines)] + result
            if lines
            else [
                (
                    False,
                    self.invoice_line_ids - group_payment_lines - group_taxes_lines,
                ),
                (group_taxes, group_taxes_lines),
                (group_payments, group_payment_lines),
            ]
        )

    def of_report_get_printable_data(self, with_payments):
        """
        Function to calculate the data to print in the invoice pdf.
        This data includes the invoice lines, totals, and tax summary.

        Args:
            with_payments (bool): Whether to include the payment group in the report.

        Returns:
            dict: Data to print in the invoice pdf.
        """
        self.ensure_one()
        invoices = self._of_report_get_linked_invoice_moves()
        group_lines = self._of_get_total_lines_by_group(invoices)
        if not with_payments:  # Remove the payment group if not needed
            group_payments = self.env['of.invoice.report.total.group'].get_payments_group()
            group_lines = [group for group in group_lines if group[0] != group_payments]
        return {
            'lines': group_lines[0][1],
            'totals': self._of_report_get_printable_totals(invoices, group_lines),
        }

    @api.model
    def _of_report_get_payment_display(self, move_line):
        """Get the description to display for a payment.
        This function is intended to be overridden in `of_account_payment` module.

        Args:
            move_line (recordset): The payment accounting entry.

        Returns:
            str: The text to display for the payment.
        """
        return _("<i>Paid on %(date)s</i>", date=move_line.date)

    def _of_report_get_printable_payments(self):
        """
        Get the payments to display in the invoice.
        This function is intended to be overridden in `of_sale` module.

        Returns:
            list: List of tuples of payments (name, amount) to display in the invoice.
        """
        account_move_line_obj = self.env['account.move.line']
        result = []
        if self.payment_state == 'invoicing_legacy':
            return result
        payments = self.sudo().invoice_payments_widget
        for payment in payments and payments.get('content') or []:
            if payment['is_exchange']:
                continue
            move_line = account_move_line_obj.browse(payment['payment_id'])
            name = self._of_report_get_payment_display(move_line)
            result.append((name, payment['amount']))
        return result

    def _of_report_get_tax_totals(self):
        """
        Get the tax values of the invoices in the recordset.

        See `account.tax._prepare_tax_totals()` for the structure of the `account.move.tax_totals`.
        """
        res = {}
        currency = self[0].currency_id
        inv_type = self[0].move_type
        for invoice in self:
            if not res:
                res = invoice.tax_totals
                continue
            totals = invoice.tax_totals
            sign = invoice.move_type == inv_type or -1
            res['amount_total'] += sign * totals['amount_total']
            res['amount_untaxed'] += sign * totals['amount_untaxed']
            for subtotal in totals['subtotals']:
                subtotal_name = subtotal['name']
                for res_subtotal in res['subtotals']:
                    if res_subtotal['name'] == subtotal_name:
                        res_subtotal['amount'] += sign * subtotal['amount']
                        for subgroup in totals['groups_by_subtotal'][subtotal_name]:
                            tax_group_id = subgroup['tax_group_id']
                            for res_subgroup in res['groups_by_subtotal'][subtotal_name]:
                                if res_subgroup['tax_group_id'] == tax_group_id:
                                    res_subgroup['tax_group_amount'] += sign * subgroup['tax_group_amount']
                                    res_subgroup['tax_group_base_amount'] += sign * subgroup['tax_group_base_amount']
                                    break
                            else:
                                res['groups_by_subtotal'][subtotal_name].append(subgroup)
                                if sign == -1:
                                    totals[subtotal_name]['tax_group_amount'] *= sign
                                    totals[subtotal_name]['tax_group_base_amount'] *= sign
                        break
                else:
                    # This case should not happen.
                    # It means we are integrating a complementary invoice including taxes not present on the final
                    # invoice.
                    res['subtotals'].append(subtotal)
                    res['groups_by_subtotal'][subtotal_name] = totals[subtotal_name]
                    if sign == -1:
                        subtotal['amount'] *= sign
                        totals[subtotal_name]['tax_group_amount'] *= sign
                        totals[subtotal_name]['tax_group_base_amount'] *= sign

        # Recompute formatted amounts
        self._of_report_recompute_formatted_amounts(res, currency)
        return res

    def _of_report_recompute_formatted_amounts(self, tax_totals, currency):
        """
        Recomputes and formats the amounts in the `tax_totals` dictionary using the provided currency.

        Args:
            tax_totals (dict): The dictionary containing tax totals.
            currency (res.currency): The currency object to be used for formatting.

        Returns:
            None
        """
        tax_totals['formatted_amount_total'] = formatLang(self.env, tax_totals['amount_total'], currency_obj=currency)
        tax_totals['formatted_amount_untaxed'] = formatLang(
            self.env, tax_totals['amount_untaxed'], currency_obj=currency
        )
        subtotals_new = []
        for subtotal in tax_totals['subtotals']:
            if not subtotal['amount']:
                del tax_totals['groups_by_subtotal'][subtotal['name']]
                continue
            subtotals_new.append(subtotal)
            subtotal['formatted_amount'] = formatLang(self.env, subtotal['amount'], currency_obj=currency)
            subtotal_group = tax_totals['groups_by_subtotal'][subtotal['name']]
            subtotal_group = [vals for vals in subtotal_group if vals['tax_group_amount']]
            for vals in subtotal_group:
                vals['formatted_tax_group_amount'] = formatLang(
                    self.env, vals['tax_group_amount'], currency_obj=currency
                )
                vals['formatted_tax_group_base_amount'] = formatLang(
                    self.env, vals['tax_group_base_amount'], currency_obj=currency
                )

    def _of_report_get_printable_taxes(self, amount_total):
        """
        Get the taxes to display in the invoice.

        Args:
            amount_total (float): The total amount of the invoice.

        Returns:
            list: List of tuples of taxes (name, amount) to display in the invoice.
        """
        currency = self[0].currency_id
        round_curr = currency.round
        result = []
        tax_totals = self._of_report_get_tax_totals()
        group_last = False
        for subtotal in tax_totals['subtotals']:
            if group_last:
                group_last[1] = (subtotal['name'], group_last[1][1])

            group_lines = []
            for line_vals in tax_totals['groups_by_subtotal'][subtotal['name']]:
                if tax_totals['display_tax_base']:
                    line_name = _(
                        "%(tax_group_name)s on %(tax_group_base_amount)s",
                        tax_group_name=line_vals['tax_group_name'],
                        tax_group_base_amount=line_vals['tax_group_base_amount'],
                    )
                else:
                    line_name = line_vals['tax_group_name']
                group_lines.append((line_name, line_vals['tax_group_amount']))
                amount_total += line_vals['tax_group_amount']
            amount_total = round_curr(amount_total)
            group_last = [group_lines, ("", amount_total)]
            result.append(group_last)
        return result

    def _of_report_get_linked_invoice_moves(self):
        """
        Get the invoices linked to the current invoice.
        Linked invoices are those for which a line is linked to the same sale order line as a line of lines.
        Any invoice linked to a linked invoice is also returned.

        Returns:
            recordset: The invoices linked to the current invoice (including the current invoice) for the pdf report.
        """
        self.ensure_one()
        return self

    def _of_report_get_printable_totals(self, moves, group_lines):
        """
        Get a dictionary containing the values to display in the totals of the invoice pdf.

        Args:
            moves (recordset): The set of invoices to use for generating the document.
            group_lines (list): The result of `self._of_get_total_lines_by_group(invoices)` to avoid recalculating.

        Returns:
            dict: The values to display in the totals of the invoice pdf.
        """
        self.ensure_one()

        # Calculate the initial subtotal and taxes title
        result = {
            'subtotal': self._of_report_calculate_ungrouped_subtotal(group_lines),
            'subtotal_title': self._of_report_get_subtotal_title(),
        }
        amount_total = result['subtotal']

        # Initialize the index for the group lines
        i = 1

        # Process untaxed subtotals
        result['untaxed'], amount_total, i = self._of_report_process_untaxed_subtotals(group_lines, amount_total, i)

        # Process taxes
        result['taxes'], amount_total, i = self._of_report_process_taxes(moves, group_lines, amount_total, i)

        # Process subtotals with taxes
        result['total'] = self._of_report_process_subtotals_with_taxes(moves, group_lines, amount_total, i)

        return result

    def _of_report_calculate_ungrouped_subtotal(self, group_lines):
        """Calculate the initial subtotal based on ungrouped lines."""
        return sum(group_lines[0][1].mapped('price_subtotal'))

    def _of_report_get_subtotal_title(self):
        """Retrieve the title for the subtotal based on tax data."""
        taxes = self.tax_totals['subtotals']
        return taxes[0]['name'] if taxes else _("Total")

    def _of_report_process_untaxed_subtotals(self, group_lines, amount_total, i):
        """Process the subtotals for untaxed lines."""
        round_curr = self.currency_id.round
        result_untaxed = []

        while i < len(group_lines) and group_lines[i][0].position == '0-pre-tax':
            group, lines = group_lines[i]
            lines_vals = [(line.of_display_name, line.price_subtotal) for line in lines]
            amount_total += sum(line.price_subtotal for line in lines)
            total_vals = (group.subtotal_name, round_curr(amount_total))
            result_untaxed.append([lines_vals, total_vals])
            i += 1

        return result_untaxed, amount_total, i

    def _of_report_process_taxes(self, moves, group_lines, amount_total, i):
        """Process the tax-related totals."""
        round_curr = self.currency_id.round

        # First group after untaxed lines should be taxes
        if i >= len(group_lines) or not group_lines[i][0].is_taxes_group():
            raise UserError(_("No group found for printing taxes"))

        group, lines = group_lines[i]
        i += 1
        result_tax = moves._of_report_get_printable_taxes(amount_total)

        if lines and not result_tax:
            result_tax = [[[], ("", amount_total)]]

        last_tax = result_tax[-1]
        amount_total = last_tax[1][1]

        for line in lines:
            amount_total += line.price_total

        last_tax[1] = (group.subtotal_name, round_curr(amount_total))

        return result_tax, amount_total, i

    def _of_report_process_subtotals_with_taxes(self, moves, group_lines, amount_total, i):
        """Process the totals including taxes."""
        round_curr = self.currency_id.round
        result_total = []

        while i < len(group_lines):
            group, lines = group_lines[i]
            i += 1
            if group.is_payments_group():
                lines_vals = moves._of_report_get_printable_payments()
                if not lines_vals:
                    continue
                for line in lines_vals:
                    amount_total -= line[1]
            else:
                lines_vals = [(line.of_display_name, line.price_total) for line in lines]
                amount_total += sum(line.price_total for line in lines)

            total_vals = (group.subtotal_name, round_curr(amount_total))
            result_total.append([lines_vals, total_vals])

        return result_total
