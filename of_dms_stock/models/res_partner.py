# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def create_pickings_directory(self):
        directory_obj = self.env["dms.directory"].with_context({"active_test": False})
        for partner in self:
            # on cherche s'il n'y a pas déjà un dossier pickings sur ce partenaire
            in_directory = directory_obj.search(
                [
                    ("parent_id", "=", partner.of_dms_directory_id.id),
                    ("res_model", "=", "stock.picking"),
                    ("of_code", "=", "incoming"),
                ]
            )
            out_directory = directory_obj.search(
                [
                    ("parent_id", "=", partner.of_dms_directory_id.id),
                    ("res_model", "=", "stock.picking"),
                    ("of_code", "=", "outgoing"),
                ]
            )
            if not in_directory:
                value_directory = {
                    "name": "Delivery Slips",
                    "res_model": "stock.picking",
                    "parent_id": partner.of_dms_directory_id.id,
                    "active": False,
                    "of_code": "incoming",
                }
                directory_obj.create(value_directory)
            if not out_directory:
                value_directory = {
                    "name": "Receipt Slips",
                    "res_model": "stock.picking",
                    "parent_id": partner.of_dms_directory_id.id,
                    "active": False,
                    "of_code": "outgoing",
                }
                directory_obj.create(value_directory)
