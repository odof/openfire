# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        data = super()._prepare_account_move_line(move=move)  # self.ensure_one()

        move_type = move.move_type if move else 'out_invoice'
        move_line_obj = self.env['account.move.line']
        account = move_line_obj._get_invoice_line_account(
            move_type, self.product_id, self.order_id.fiscal_position_id, self.company_id
        )
        if tax_ids := data['tax_ids']:
            for tax in self.env['account.tax'].browse(tax_ids[0][2]):
                account = tax.map_account(account)
        if account:
            data['account_id'] = account.id
        return data
