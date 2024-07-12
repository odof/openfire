# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFServiceRequest(models.Model):
    _inherit = "of.service.request"

    def update_dms_files(self):
        directory_obj = self.env["dms.directory"]
        file_obj = self.env["dms.file"]
        for service in self:
            # on cherche des fichiers qui existent déjà ou pas
            files = file_obj.search(
                [
                    "|",
                    "&",
                    "&",
                    ("of_type", "=", "virtual"),
                    ("of_virtual_res_model.model", "=", "of.service.request"),
                    ("of_virtual_res_id", "=", service.id),
                    "&",
                    "&",
                    ("of_type", "=", "real"),
                    ("attachment_id.res_model", "=", "of.service.request"),
                    ("attachment_id.res_id", "=", service.id),
                ]
            )

            if files:
                if not service.partner_id.of_dms_directory_id:
                    service.partner_id.create_partners_directory()

                if not service.partner_id.of_dms_directory_id.active:
                    service.partner_id.of_dms_directory_id.active = True

                service_directories = (
                    service.with_context(active_test=False)
                    .mapped("partner_id.of_dms_directory_id.child_directory_ids")
                    .filtered(lambda r: r.res_model == "of.service.request")
                )

                # si on n'a pas de dossier DI, il faut le créer
                if not service_directories:
                    service_directory = directory_obj.create(
                        {
                            "name": "Service Requests",
                            "res_model": "of.service.request",
                            "parent_id": service.partner_id.of_dms_directory_id.id,
                            "active": True,
                        }
                    )
                else:
                    service_directory = service_directories[0]

                if not service_directory.active:
                    service_directory.active = True

                directories_to_update = files.mapped("directory_id")
                files.write({"directory_id": service_directory.id})
                # on archive les dossiers qui n'ont plus de fichier
                directories_to_update.update_dms_directories()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env["dms.file"].create_dms_files("of.service.request", res.ids, "partner_id", "Service Requests")
        return res

    def write(self, vals):
        """
        Quand on change le partenaire d'une DI, on déplace dans le fichier DMS associé
        dans le dossier du nouveau partenaire.
        """
        res = super().write(vals)
        if "partner_id" in vals:
            self.update_dms_files()
        return res
