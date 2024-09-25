# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class OFInvoiceReportTotalGroup(models.Model):
    _name = 'of.invoice.report.total.group'
    _description = "Printing sales invoice totals"
    _order = 'position, sequence'

    name = fields.Char(translate=True)
    subtotal_name = fields.Char(translate=True)
    sequence = fields.Integer(default=10)
    product_ids = fields.Many2many(comodel_name='product.product', string="Filter on products")
    categ_ids = fields.Many2many(comodel_name='product.category', string="Filter on categories")
    is_affect_invoice = fields.Boolean(string="Affects invoices", default=True)
    is_affect_order = fields.Boolean(string="Affects sale orders")
    position = fields.Selection(
        selection=[('0-pre-tax', "Untaxed"), ('1-post-tax', "Tax included")], required=True, default='1-post-tax'
    )

    @api.model
    def get_payments_group(self):
        return (
            self.env.ref(
                'of_account_sale_report_totals.of_invoice_report_total_group_payments', raise_if_not_found=False
            )
            or self.browse()
        )

    @api.model
    def get_taxes_group(self):
        return (
            self.env.ref('of_account_sale_report_totals.of_invoice_report_total_group_taxes', raise_if_not_found=False)
            or self.browse()
        )

    def is_payments_group(self):
        return self == self.get_payments_group()

    def is_taxes_group(self):
        return self == self.get_taxes_group()

    def filter_lines(self, lines, invoices=None):
        """
        Filters the received lines according to the allowed articles/categories for the current group.
        """

        def hax_no_tax_amount(line):
            return float_compare(line.price_subtotal, line.price_total, precision_digits=2) == 0

        def product_in_group(line):
            return line.product_id in self.product_ids or line.product_id.categ_id in self.categ_ids

        self.ensure_one()
        if self.is_payments_group():
            # We do not allow articles in payments. (See module `of_sale` for this possibility)
            return False
        if self.position == '1-post-tax':
            # We do not allow lines with a tax amount in the "with tax" groups.
            lines = lines.filtered(hax_no_tax_amount)
        return lines.filtered(product_in_group)
