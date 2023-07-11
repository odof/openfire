# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_invoice_line_account(self, move_type=False, product=False, fiscal_position=False, company=False):
        product = product.with_company(company or self.env.company)
        is_sale_document = move_type in self.env['account.move'].get_sale_types(include_receipts=True)

        accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
        return accounts['income'] if is_sale_document else accounts['expense']

    @api.depends('display_type', 'company_id', 'tax_ids')
    def _compute_account_id(self):
        super()._compute_account_id()
        for line in self:
            account = line.account_id
            if line.product_id and line.tax_ids:
                account = self._get_invoice_line_account(
                    line.move_id.move_type, line.product_id, line.move_id.fiscal_position_id, line.company_id
                )
                for tax in line.tax_ids:
                    account = tax.map_account(account)
            if line.account_id != account:
                line.account_id = account
