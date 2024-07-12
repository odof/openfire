# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def create_invoices_directory(self):
        directory_obj = self.env["dms.directory"].with_context({"active_test": False})
        for partner in self:
            # on cherche s'il n'y a pas déjà un dossier moves sur ce partenaire
            in_directory = directory_obj.search(
                [
                    ("parent_id", "=", partner.of_dms_directory_id.id),
                    ("res_model", "=", "account.move"),
                    ("of_code", "=", "IN"),
                ]
            )
            out_directory = directory_obj.search(
                [
                    ("parent_id", "=", partner.of_dms_directory_id.id),
                    ("res_model", "=", "account.move"),
                    ("of_code", "=", "OUT"),
                ]
            )
            if not in_directory:
                value_directory = {
                    "name": "Vendor Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": partner.of_dms_directory_id.id,
                    "active": False,
                    "of_code": "IN",
                }
                directory_obj.create(value_directory)
            if not out_directory:
                value_directory = {
                    "name": "Customer Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": partner.of_dms_directory_id.id,
                    "active": False,
                    "of_code": "OUT",
                }
                directory_obj.create(value_directory)
