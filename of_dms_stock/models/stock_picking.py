# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def update_dms_files(self):
        directory_obj = self.env["dms.directory"]
        file_obj = self.env["dms.file"]
        for picking in self:
            # on cherche des fichiers qui existent déjà ou pas
            files = file_obj.search(
                [
                    "|",
                    "&",
                    "&",
                    ("of_type", "=", "virtual"),
                    ("of_virtual_res_model.model", "=", "stock.picking"),
                    ("of_virtual_res_id", "=", picking.id),
                    "&",
                    "&",
                    ("of_type", "=", "real"),
                    ("attachment_id.res_model", "=", "stock.picking"),
                    ("attachment_id.res_id", "=", picking.id),
                ]
            )

            if files and picking.partner_id:
                if not picking.partner_id.of_dms_directory_id:
                    picking.partner_id.create_partners_directory()

                if not picking.partner_id.of_dms_directory_id.active:
                    picking.partner_id.of_dms_directory_id.active = True

                picking_directories = (
                    picking.with_context(active_test=False)
                    .mapped("partner_id.of_dms_directory_id.child_directory_ids")
                    .filtered(lambda r: r.res_model == "stock.picking")
                )

                # si on n'a pas de dossier pickings, il faut le créer
                if not picking_directories:
                    picking_directory = directory_obj.create(
                        {
                            "name": "Receipt Slips" if picking.picking_type_code == "incoming" else "Delivery Slips",
                            "res_model": "stock.picking",
                            "parent_id": picking.partner_id.of_dms_directory_id.id,
                            "active": True,
                            "of_code": picking.picking_type_code,
                        }
                    )
                else:
                    picking_directory = picking_directories[0]

                if not picking_directory.active:
                    picking_directory.active = True

                directories_to_update = files.mapped("directory_id")
                files.write({"directory_id": picking_directory.id})
                # on archive les dossiers qui n'ont plus de fichier
                directories_to_update.update_dms_directories()

    @api.model_create_multi
    def create(self, vals_list):
        file_obj = self.env["dms.file"]
        res = super().create(vals_list)
        in_pickings = res.filtered(lambda r: r.picking_type_code == "incoming")
        out_pickings = res.filtered(lambda r: r.picking_type_code == "outgoing")
        if out_pickings:
            file_obj.create_dms_files("stock.picking", out_pickings.ids, "partner_id", "Delivery Slips", "outgoing")
        if in_pickings:
            file_obj.create_dms_files("stock.picking", in_pickings.ids, "partner_id", "Receipt Slips", "incoming")
        return res

    def write(self, vals):
        """
        Quand on change le partenaire d'un BL/BR, on déplace dans le fichier DMS associé
        dans le dossier du nouveau partenaire.
        """
        res = super().write(vals)
        if "partner_id" in vals:
            filtered_pickings = self.filtered(lambda r: r.picking_type_code in ["incoming", "outgoing"])
            if filtered_pickings:
                filtered_pickings.update_dms_files()
        return res
