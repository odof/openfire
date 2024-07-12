# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def update_dms_files(self):
        directory_obj = self.env["dms.directory"]
        file_obj = self.env["dms.file"]
        for purchase in self:
            # on cherche des fichiers qui existent déjà ou pas
            files = file_obj.search(
                [
                    "|",
                    "&",
                    "&",
                    ("of_type", "=", "virtual"),
                    ("of_virtual_res_model.model", "=", "purchase.order"),
                    ("of_virtual_res_id", "=", purchase.id),
                    "&",
                    "&",
                    ("of_type", "=", "real"),
                    ("attachment_id.res_model", "=", "purchase.order"),
                    ("attachment_id.res_id", "=", purchase.id),
                ]
            )

            if files:
                if not purchase.partner_id.of_dms_directory_id:
                    purchase.partner_id.create_partners_directory()

                if not purchase.partner_id.of_dms_directory_id.active:
                    purchase.partner_id.of_dms_directory_id.active = True

                purchase_directories = (
                    purchase.with_context(active_test=False)
                    .mapped("partner_id.of_dms_directory_id.child_directory_ids")
                    .filtered(lambda r: r.res_model == "purchase.order")
                )

                # si on n'a pas de dossier purchases, il faut le créer
                if not purchase_directories:
                    purchase_directory = directory_obj.create(
                        {
                            "name": "Purchases",
                            "res_model": "purchase.order",
                            "parent_id": purchase.partner_id.of_dms_directory_id.id,
                            "active": True,
                        }
                    )
                else:
                    purchase_directory = purchase_directories[0]

                if not purchase_directory.active:
                    purchase_directory.active = True

                directories_to_update = files.mapped("directory_id")
                files.write({"directory_id": purchase_directory.id})
                # on archive les dossiers qui n'ont plus de fichier
                directories_to_update.update_dms_directories()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env["dms.file"].create_dms_files("purchase.order", res.ids, "partner_id", "Purchases")
        return res

    def write(self, vals):
        """
        Quand on change le partenaire d'une commande d'achat, on déplace dans le fichier DMS associé
        dans le dossier du nouveau partenaire.
        """
        res = super().write(vals)
        if "partner_id" in vals:
            self.update_dms_files()
        return res
