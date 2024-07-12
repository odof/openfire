# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.dms.tools import file


class DMSFile(models.Model):
    _inherit = "dms.file"

    of_type = fields.Selection(
        selection=[("real", "Real"), ("virtual", "Virtual")], default="real", string="Type of file"
    )
    of_content_url = fields.Char(string="Content URL", compute="_compute_of_content_url")
    of_virtual_res_model = fields.Many2one(comodel_name="ir.model", string="Model")
    of_virtual_res_id = fields.Integer(string="Virtual ID")
    of_virtual_report_name = fields.Char(string="File Report Name")
    content = fields.Binary(required=False)

    def _check_name(self):
        """Remplace la fonction _check_name originale pour supprimer la contrainte sur les noms identiques"""
        for record in self:
            if not file.check_name(record.name):
                raise ValidationError(_("The file name is invalid."))

    @api.depends("of_type", "of_virtual_res_id", "of_virtual_res_model", "attachment_id")
    def _compute_of_content_url(self):
        for record in self:
            if record.of_type == "virtual" and record.of_virtual_res_id and record.of_virtual_res_model:
                # on va chercher dans la configuration le rapport associé
                if record.of_virtual_report_name:
                    record.of_content_url = f"/report/html/{record.of_virtual_report_name}/{record.of_virtual_res_id}"
                else:
                    record.of_content_url = False
            else:
                if "pdf" in record.mimetype:
                    record.of_content_url = (
                        f"/web/static/lib/pdfjs/web/viewer.html?file=/web/content/{record.attachment_id.id}"
                    )
                elif "image" in record.mimetype:
                    record.of_content_url = f"/web/image/{record.attachment_id.id}"
                else:
                    record.of_content_url = "/of_dms_view/static/images/binary_file.png"

    @api.depends("content_binary", "content_file", "attachment_id")
    def _compute_content(self):
        bin_size = self.env.context.get("bin_size", False)
        for record in self:
            if record.of_type == "real":
                if record.content_file:
                    context = {"human_size": True} if bin_size else {"base64": True}
                    record.content = record.with_context(**context).content_file
                elif record.content_binary:
                    record.content = record.content_binary if bin_size else base64.b64encode(record.content_binary)
                elif record.attachment_id:
                    context = {"human_size": True} if bin_size else {"base64": True}
                    record.content = record.with_context(**context).attachment_id.datas
            else:
                # TODO : peut-être mettre dedans l"image qui représente un fichier virtuel ?
                record.content = " "

    def create_dms_files(self, res_model, res_ids, partner_field, directory_name, code=False):
        """Créer les fichiers DMS virtuels et réels

        Args:
            res_model (char): le nom du modèle
            res_ids (list): la liste des ids
            partner_field (char): le nom du champ partenaire, nécessaire pour retrouver le dossier DMS
            directory_name (char): le nom  a donné au dossier, si besoin de le créer
        """
        file_report_obj = self.env["of.dms.virtual_file_report"]
        file_obj = self.env["dms.file"]
        directory_obj = self.env["dms.directory"]
        attachment_obj = self.env["ir.attachment"]
        model_obj = self.env["ir.model"]

        model = model_obj.search([("model", "=", res_model)], limit=1)

        # le nom du fichier doit respecter le nommage du rapport
        virtual_reports = file_report_obj.search(
            [("company_id", "=", self.env.user.company_id.id), ("model_id", "=", model.id)]
        )

        records = self.env[res_model].browse(res_ids)

        for record in records:
            partner = record[partner_field]

            if partner:
                if not partner.of_dms_directory_id:
                    partner.create_partners_directory()

                if not partner.of_dms_directory_id.active:
                    partner.of_dms_directory_id.active = True

                record_directories = (
                    partner.with_context(active_test=False)
                    .mapped("of_dms_directory_id.child_directory_ids")
                    .filtered(lambda r: r.res_model == res_model and r.of_code == code)
                )

                # si on n'a pas de dossier records, il faut le créer
                if not record_directories:
                    record_directory = directory_obj.create(
                        {
                            "name": directory_name,
                            "res_model": res_model,
                            "parent_id": partner.of_dms_directory_id.id,
                            "active": True,
                            "of_code": code,
                        }
                    )
                else:
                    record_directory = record_directories[0]

                if not record_directory.active:
                    record_directory.active = True

                # on va chercher également s'il y a des pièces jointes sur ce record, pour les ajouter
                attachments = attachment_obj.search([("res_model", "=", res_model), ("res_id", "=", record.id)])
                attachments.create_dms_files(partner=partner)

                for virtual_report in virtual_reports:
                    if virtual_report.report_id.print_report_name:
                        report_name = safe_eval(
                            virtual_report.report_id.print_report_name,
                            {
                                "object": record,
                                "time": time,
                            },
                        )
                        filename = f"{report_name}.pdf"
                    else:
                        filename = f"{record.display_name}.pdf"
                    filename = filename.replace("/", "_")
                    # on cherche si le fichier virtuel existe déjà ou pas
                    virtual_file = file_obj.search(
                        [
                            ("name", "=", filename),
                            ("of_type", "=", "virtual"),
                            ("directory_id", "=", record_directory.id),
                            ("of_virtual_res_model.model", "=", res_model),
                            ("of_virtual_res_id", "=", record.id),
                            ("of_virtual_report_name", "=", virtual_report.report_id.report_name),
                        ]
                    )
                    if not virtual_file:
                        value_file = {
                            "name": filename,
                            "of_type": "virtual",
                            "directory_id": record_directory.id,
                            "of_virtual_res_model": model.id,
                            "of_virtual_res_id": record.id,
                            "of_virtual_report_name": virtual_report.report_id.report_name,
                        }
                        file_obj.create(value_file)
