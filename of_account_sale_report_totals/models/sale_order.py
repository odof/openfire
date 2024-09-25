# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class SaleOrder(models.Model):
    """Methods that are starts with `_of_report_` are used in the report template."""

    _name = 'sale.order'
    _inherit = ['sale.order', 'of.account.sale.report.totals.mixin']

    # --------------------------------------------------------------------------
    # Report methods
    # --------------------------------------------------------------------------

    def _of_get_total_lines_by_group(self):
        """
        Returns the order lines, separated according to the group in which they should be displayed.

        The groups are those defined by the `of.invoice.report.total` object, allowing to move the rendering of the
        order lines under the total excluding tax or including tax.

        Groups are displayed in their own order, then the lines in the order of appearance in the order.

        Returns:
            list: List of tuples (group, order lines).
                The first element is (False, Ungrouped lines).
        """
        self.ensure_one()
        group_obj = self.env['of.invoice.report.total.group']
        move_line_obj = self.env['account.move.line']

        order_lines = self._get_order_lines_to_report()  # Get same lines as in the standard report
        products = order_lines.mapped('product_id')
        product_ids = list(products.ids)
        categ_ids = list(products.mapped('categ_id').ids)
        group_payments = group_obj.get_payments_group()
        group_taxes = group_obj.get_taxes_group()
        groups = group_obj.search(
            [
                ('is_affect_order', '=', True),
                '|',
                '|',
                ('id', 'in', (group_payments.id, group_taxes.id)),
                ('product_ids', 'in', product_ids),
                ('categ_ids', 'in', categ_ids),
            ]
        )

        result = []
        group_taxes_lines = move_line_obj

        # Remove payment lines from the order lines
        for group in groups:
            if group.is_payments_group():
                group_paiement_lines = group.filter_lines(order_lines)
                if group_paiement_lines is not False:
                    order_lines -= group_paiement_lines
                break

        # Split lines into groups
        for group in groups:
            if group.is_payments_group():
                result.append((group, group_paiement_lines))
            else:
                group_lines = group.filter_lines(order_lines)
                if group_lines or group.is_taxes_group():
                    # We don't want to display payment lines with a total of 0 and we don't want to display the group
                    # if all lines are at 0.
                    if group_lines_with_subtotal := group_lines.filtered(lambda line: line.price_subtotal):
                        result.append((group, group_lines_with_subtotal))
                    # Remove all lines of the group so they don't get displayed outside of the group
                    order_lines -= group_lines
                if group.is_taxes_group():
                    group_taxes_lines |= group_lines

        if order_lines:
            return [(False, order_lines)] + result

        result = [(False, self.order_line.mapped('invoice_lines'))]

        # We add the payments anyway
        for group in groups:
            if group.is_payments_group():
                result.append((group, order_lines))  # order_lines is empty here
        return result

    def of_report_get_printable_data(self):
        """
        Function to calculate the data to print in the sale order pdf.
        This data includes the order lines, totals, and tax summary.

        Returns:
            dict: Data to print in the invoice pdf.
        """
        self.ensure_one()
        group_lines = self._of_get_total_lines_by_group()
        return {
            'lines': group_lines[0][1],
            'totals': self._of_report_get_printable_totals(group_lines),
        }

    def _of_report_get_printable_payments(self, order_lines):
        """
        Returns the lines to display.

        Allows the display of payments in an order.
        """
        move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']

        # Get all the invoices and credit notes
        moves = self.mapped('order_line').mapped('invoice_lines').mapped('move_id')

        result = []
        for move in moves:
            payment_widget_vals = move.invoice_payments_widget
            if not payment_widget_vals:
                continue
            for payment in payment_widget_vals.get('content', []):
                # Les paiements sont classés dans l'ordre chronologique
                move_line = account_move_line_obj.browse(payment['payment_id'])
                name = move_obj._of_report_get_payment_display(move_line)
                result.append((name, payment['amount']))
        return result

    def _of_report_get_printable_taxes(self, amount_total):
        currency = self.currency_id
        round_curr = currency.round
        result = []
        tax_totals = self.tax_totals
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

    def _of_report_get_printable_totals(self, group_lines):
        """
        Get a dictionary containing the values to display in the totals of the sale order pdf.

        Args:
            group_lines (list): The result of `self._of_get_total_lines_by_group(invoices)` to avoid recalculating.

        Returns:
            dict: The values to display in the totals of the sale order pdf.
        """
        self.ensure_one()

        result = {
            'subtotal': self._of_report_calculate_ungrouped_subtotal(group_lines),
            'subtotal_title': self._of_report_get_subtotal_title(),
        }
        amount_total = result['subtotal']

        i = 1

        # Processing untaxed subtotals
        result['untaxed'], amount_total, i = self._of_report_process_untaxed_subtotals(group_lines, amount_total, i)

        # Processing taxes
        result['taxes'], amount_total, i = self._of_report_process_taxes(group_lines, amount_total, i)

        # Processing total subtotals including taxes
        result['total'] = self._of_report_process_subtotals_with_taxes(group_lines, amount_total, i)

        return result

    def _of_report_process_taxes(self, group_lines, amount_total, i):
        """Process the tax-related totals."""
        round_curr = self.currency_id.round

        group, lines = group_lines[i]
        result_tax = self._of_report_get_printable_taxes(amount_total)

        if lines and not result_tax:
            result_tax = [[[], ('', amount_total)]]

        last_tax = result_tax[-1]
        amount_total = last_tax[1][1]

        for line in lines:
            amount_total += line.price_total

        last_tax[1] = (group.subtotal_name, round_curr(amount_total))
        return result_tax, amount_total, i

    def _of_report_process_subtotals_with_taxes(self, group_lines, amount_total, i):
        """Process the totals including taxes."""
        round_curr = self.currency_id.round
        result_total = []

        while i < len(group_lines):
            group, lines = group_lines[i]
            i += 1
            if group.is_payments_group():
                lines_vals = self._of_report_get_printable_payments(lines)
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

    def _of_get_printable_totals(self):
        """[IMPRESSION]
        Retourne un dictionnaire contenant les valeurs à afficher dans les totaux de la commande pdf.
        Dictionnaire de la forme :
        {
            'subtotal' : Total HT des lignes affichées,
            'untaxed' : [[('libellé', montant),...], ('libellé total': montant_total)]
            'taxes' : idem,
            'total' : idem,
        }
        Les listes untaxed, taxes et total pourraient être regroupés en une seule.
        Ce format pourra aider aux héritages (?).
        """
        self.ensure_one()
        tax_obj = self.env['account.tax']
        round_curr = self.currency_id.round

        group_lines = self._of_get_total_lines_by_group()

        result = {'subtotal': sum(group_lines[0][1].mapped('price_subtotal'))}
        total_amount = result['subtotal']

        i = 1
        untaxed_lines = group_lines[0][1]
        # --- Sous-totaux hors taxes ---
        result_untaxed = []
        while i < len(group_lines) and group_lines[i][0].position == '0-ht':
            group, lines = group_lines[i]
            i += 1
            untaxed_lines |= lines
            lines_vals = []
            for line in lines:
                lines_vals.append((line.of_get_line_name()[0], line.price_subtotal))
                total_amount += line.price_subtotal
            total_vals = (group.subtotal_name, round_curr(total_amount))
            result_untaxed.append([lines_vals, total_vals])
        result['untaxed'] = result_untaxed

        # --- Ajout des taxes ---
        # Code copié depuis account.invoice.get_taxes_values()
        tax_grouped = {}
        for line in untaxed_lines:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(
                price_unit, self.currency_id, line.product_uom_qty, line.product_id, self.partner_id
            )['taxes']
            for tax_val in taxes:
                val = self._prepare_tax_line_vals(line, tax_val)
                tax = tax_obj.browse(tax_val['id'])
                key = tax.get_grouping_key(val)

                val['amount'] += val['base'] - round_curr(val['base'])
                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['name'] = tax.description or tax.name
                    tax_grouped[key]['group'] = tax.tax_group_id
                else:
                    tax_grouped[key]['amount'] += val['amount']
        # Taxes groupées par groupe de taxes (cf account.invoice._get_tax_amount_by_group())
        tax_vals_dict = {}
        for tax in sorted(tax_grouped.values(), key=lambda t: t['name']):
            amount = round_curr(tax['amount'])
            tax_vals_dict.setdefault(tax['group'], [tax['group'].name, 0])
            tax_vals_dict[tax['group']][1] += amount
            total_amount += amount
        result['taxes'] = [[tax_vals_dict.values(), (_("Total TTC"), round_curr(total_amount))]]

        # --- Sous-totaux TTC ---
        result_total = []
        while i < len(group_lines):
            # Tri des paiements par date
            group, lines = group_lines[i]
            i += 1
            if group.is_payments_group():
                lines_vals = self._of_get_printable_payments(lines)
                if not lines_vals:
                    continue
                for line in lines_vals:
                    total_amount -= line[1]
            else:
                lines_vals = []
                for line in lines:
                    lines_vals.append((line.of_get_line_name()[0], line.price_total))
                    total_amount += line.price_total
            total_vals = (group.subtotal_name, round_curr(total_amount))
            result_total.append([lines_vals, total_vals])
        result['total'] = result_total

        return result
