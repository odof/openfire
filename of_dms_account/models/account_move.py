# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def update_dms_files(self):
        directory_obj = self.env["dms.directory"]
        file_obj = self.env["dms.file"]
        for invoice in self:
            # on cherche des fichiers qui existent déjà ou pas
            files = file_obj.search(
                [
                    "|",
                    "&",
                    "&",
                    ("of_type", "=", "virtual"),
                    ("of_virtual_res_model.model", "=", "account.move"),
                    ("of_virtual_res_id", "=", invoice.id),
                    "&",
                    "&",
                    ("of_type", "=", "real"),
                    ("attachment_id.res_model", "=", "account.move"),
                    ("attachment_id.res_id", "=", invoice.id),
                ]
            )

            if files:
                if not invoice.partner_id.of_dms_directory_id:
                    invoice.partner_id.create_partners_directory()

                if not invoice.partner_id.of_dms_directory_id.active:
                    invoice.partner_id.of_dms_directory_id.active = True

                invoice_directories = (
                    invoice.with_context(active_test=False)
                    .mapped("partner_id.of_dms_directory_id.child_directory_ids")
                    .filtered(lambda r: r.res_model == "account.move")
                )

                # si on n'a pas de dossier invoices, il faut le créer
                if not invoice_directories:
                    invoice_directory = directory_obj.create(
                        {
                            "name": (
                                "Customer Invoices & Refunds"
                                if invoice.move_type in ["out_invoice", "out_refund"]
                                else "Vendor Invoices & Refunds"
                            ),
                            "res_model": "account.move",
                            "parent_id": invoice.partner_id.of_dms_directory_id.id,
                            "active": True,
                            "of_code": "OUT" if invoice.move_type in ["out_invoice", "out_refund"] else "IN",
                        }
                    )
                else:
                    invoice_directory = invoice_directories[0]

                if not invoice_directory.active:
                    invoice_directory.active = True

                directories_to_update = files.mapped("directory_id")
                files.write({"directory_id": invoice_directory.id})
                # on archive les dossiers qui n'ont plus de fichier
                directories_to_update.update_dms_directories()

    @api.model_create_multi
    def create(self, vals_list):
        file_obj = self.env["dms.file"]
        res = super().create(vals_list)
        in_res = res.filtered(lambda r: r.move_type in ["in_invoice", "in_refund"])
        out_res = res.filtered(lambda r: r.move_type in ["out_invoice", "out_refund"])
        if out_res:
            file_obj.create_dms_files("account.move", out_res.ids, "partner_id", "Customer Invoices & Refunds", "OUT")
        if in_res:
            file_obj.create_dms_files("account.move", in_res.ids, "partner_id", "Vendor Invoices & Refunds", "IN")
        return res

    def write(self, vals):
        """
        Quand on change le partenaire d'une facture, on déplace dans le fichier DMS associé
        dans le dossier du nouveau partenaire.
        """
        res = super().write(vals)
        if "partner_id" in vals:
            filtered_invoices = self.filtered(
                lambda r: r.move_type in ["in_invoice", "in_refund", "out_invoice", "out_refund"]
            )
            if filtered_invoices:
                filtered_invoices.update_dms_files()
        return res
