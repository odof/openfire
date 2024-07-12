# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def create_interventions_directory(self):
        directory_obj = self.env["dms.directory"].with_context({"active_test": False})
        for partner in self:
            # on cherche s'il n'y a pas déjà un dossier intervention sur ce partenaire
            directory = directory_obj.search(
                [("parent_id", "=", partner.of_dms_directory_id.id), ("res_model", "=", "calendar.event")]
            )
            if not directory:
                value_directory = {
                    "name": "Interventions",
                    "res_model": "calendar.event",
                    "parent_id": partner.of_dms_directory_id.id,
                    "active": False,
                }
                directory_obj.create(value_directory)
