# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def update_dms_files(self):
        directory_obj = self.env["dms.directory"]
        file_obj = self.env["dms.file"]
        for intervention in self:
            # on cherche des fichiers qui existent déjà ou pas
            files = file_obj.search(
                [
                    "|",
                    "&",
                    "&",
                    ("of_type", "=", "virtual"),
                    ("of_virtual_res_model.model", "=", "calendar.event"),
                    ("of_virtual_res_id", "=", intervention.id),
                    "&",
                    "&",
                    ("of_type", "=", "real"),
                    ("attachment_id.res_model", "=", "calendar.event"),
                    ("attachment_id.res_id", "=", intervention.id),
                ]
            )

            if files:
                if not intervention.of_partner_id.of_dms_directory_id:
                    intervention.of_partner_id.create_partners_directory()

                if not intervention.of_partner_id.of_dms_directory_id.active:
                    intervention.of_partner_id.of_dms_directory_id.active = True

                intervention_directories = (
                    intervention.with_context(active_test=False)
                    .mapped("of_partner_id.of_dms_directory_id.child_directory_ids")
                    .filtered(lambda r: r.res_model == "calendar.event")
                )

                # si on n'a pas de dossier interventions, il faut le créer
                if not intervention_directories:
                    intervention_directory = directory_obj.create(
                        {
                            "name": "Interventions",
                            "res_model": "calendar.event",
                            "parent_id": intervention.of_partner_id.of_dms_directory_id.id,
                            "active": True,
                        }
                    )
                else:
                    intervention_directory = intervention_directories[0]

                if not intervention_directory.active:
                    intervention_directory.active = True

                directories_to_update = files.mapped("directory_id")
                files.write({"directory_id": intervention_directory.id})
                # on archive les dossiers qui n'ont plus de fichier
                directories_to_update.update_dms_directories()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env["dms.file"].create_dms_files("calendar.event", res.ids, "of_partner_id", "Interventions")
        return res

    def write(self, vals):
        """
        Quand on change le partenaire d'une intervention, on déplace dans le fichier DMS associé
        dans le dossier du nouveau partenaire.
        """
        res = super().write(vals)
        if "of_partner_id" in vals:
            self.update_dms_files()
        return res
