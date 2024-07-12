# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_dms_directory_id = fields.Many2one(comodel_name="dms.directory", string="Directory in DMS", ondelete="cascade")

    def create_partners_directory(self):
        for partner in self:
            # on regarde si le dossier partner n'existe pas déjà
            if not partner.of_dms_directory_id:
                directory = self.env["dms.directory"].create(
                    {
                        "name": f"{partner.name}",
                        "parent_id": self.env.ref("of_dms.directory_contacts").id,
                        "active": False,
                        "res_model": "res.partner",
                        "res_id": partner.id,
                    }
                )
                partner.of_dms_directory_id = directory.id

            # on va chercher également s'il y a des pièces jointes sur ce partner, pour les ajouter
            attachments = self.env["ir.attachment"].search(
                [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
            )
            attachments.create_dms_files(partner=partner)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners.create_partners_directory()
        return partners

    def write(self, vals):
        # si on archive le partenaire, on archive aussi son dossier
        if "active" in vals:
            self.of_dms_directory_id.active = vals.get("active")
        return super().write(vals)
