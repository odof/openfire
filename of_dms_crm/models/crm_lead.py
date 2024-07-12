# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class CRMLead(models.Model):
    _inherit = "crm.lead"

    def update_dms_files(self):
        directory_obj = self.env["dms.directory"]
        file_obj = self.env["dms.file"]
        for lead in self:
            # on cherche des fichiers qui existent déjà ou pas
            files = file_obj.search(
                [
                    "|",
                    "&",
                    "&",
                    ("of_type", "=", "virtual"),
                    ("of_virtual_res_model.model", "=", "crm.lead"),
                    ("of_virtual_res_id", "=", lead.id),
                    "&",
                    "&",
                    ("of_type", "=", "real"),
                    ("attachment_id.res_model", "=", "crm.lead"),
                    ("attachment_id.res_id", "=", lead.id),
                ]
            )

            if files:
                if not lead.partner_id.of_dms_directory_id:
                    lead.partner_id.create_partners_directory()

                if not lead.partner_id.of_dms_directory_id.active:
                    lead.partner_id.of_dms_directory_id.active = True

                lead_directories = (
                    lead.with_context(active_test=False)
                    .mapped("partner_id.of_dms_directory_id.child_directory_ids")
                    .filtered(lambda r: r.res_model == "crm.lead")
                )

                # si on n'a pas de dossier leads, il faut le créer
                if not lead_directories:
                    lead_directory = directory_obj.create(
                        {
                            "name": "Leads",
                            "res_model": "crm.lead",
                            "parent_id": lead.partner_id.of_dms_directory_id.id,
                            "active": True,
                        }
                    )
                else:
                    lead_directory = lead_directories[0]

                if not lead_directory.active:
                    lead_directory.active = True

                directories_to_update = files.mapped("directory_id")
                files.write({"directory_id": lead_directory.id})
                # on archive les dossiers qui n'ont plus de fichier
                directories_to_update.update_dms_directories()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env["dms.file"].create_dms_files("crm.lead", res.ids, "partner_id", "Leads")
        return res

    def write(self, vals):
        """
        Quand on change le partenaire d'une opportunité, on déplace dans le fichier DMS associé
        dans le dossier du nouveau partenaire.
        """
        res = super().write(vals)
        if "partner_id" in vals:
            self.update_dms_files()
        return res
