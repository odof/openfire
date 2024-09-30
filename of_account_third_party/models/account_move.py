# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("partner_id", "company_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            if self.move_type == "out_invoice":  # Customer Invoice
                self.partner_id.update_account(update_customer_account=True)
            elif self.move_type == "in_invoice":  # Supplier invoice
                self.partner_id.update_account(update_supplier_account=True)
        return super()._onchange_partner_id()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if partner_id := vals.get("partner_id"):
                partner = self.env["res.partner"].browse(partner_id)
                if vals.get("move_type") == "out_invoice":  # Customer Invoice
                    partner.update_account(update_customer_account=True)
                elif vals.get("move_type") == "in_invoice":  # Supplier invoice
                    partner.update_account(update_supplier_account=True)
        return super().create(vals_list)
