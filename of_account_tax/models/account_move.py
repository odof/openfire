# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("fiscal_position_id")
    def _onchange_fiscal_position_id(self):
        if self.fiscal_position_id:
            for line in self.invoice_line_ids:
                taxes = line._get_computed_taxes()
                company_id = self.company_id or self.env.user.company_id
                taxes = company_id._of_filter_taxes(taxes)
                line.tax_ids = self.fiscal_position_id.map_tax(taxes)
