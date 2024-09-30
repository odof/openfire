# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    of_account_ids = fields.One2many(
        comodel_name="of.account.tax.account", inverse_name="tax_id", string="Account matching", copy=True
    )

    def map_account(self, account):
        self.ensure_one()
        return next(
            (pos.account_dest_id for pos in self.of_account_ids if pos.account_src_id == account),
            account,
        )
