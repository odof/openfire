# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class ReportTotalsMixin(models.AbstractModel):
    """Mixin for Report Totals to be used in sale/account reports."""

    _name = 'of.account.sale.report.totals.mixin'
    _description = "Mixin for Report Totals"

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
