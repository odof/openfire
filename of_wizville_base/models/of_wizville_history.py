# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import csv

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

try:
    from io import StringIO
except ImportError:
    from io import StringIO

try:
    import chardet
except ImportError:
    chardet = None

import logging
import os
import tempfile

import paramiko

_logger = logging.getLogger(__name__)


class OFWizvilleHistory(models.Model):
    _name = "of.wizville.history"
    _description = "Wizville History"
    _order = "date"

    name = fields.Char(related="file_name_wizville", readonly=True)
    type = fields.Selection(
        [
            ("import", "Import"),
            ("export", "Export"),
        ],
        string="Export/Import",
        required=True,
    )
    file_name_wizville = fields.Char(string="Wizville File Name", size=100)
    file_wizville = fields.Binary(string="Wizville File", attachment=True)
    is_done = fields.Boolean(string="Export Done")
    date = fields.Date(string="Export Date", default=fields.Date.today())

    def put_file_wizville(self):
        self.ensure_one()
        # Récupération des infos de connexion SFTP
        ir_default_obj = self.env["ir.default"]
        sftp_host = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_host")
        sftp_port = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_port")
        sftp_user = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_user")
        sftp_password = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_password")

        if not sftp_host or not sftp_port or not sftp_user or not sftp_password:
            return

        # Recherche de l'attachement à uploader
        file_attachment = self.env["ir.attachment"].search(
            [("res_model", "=", "of.wizville.history"), ("res_id", "=", self.id), ("res_field", "=", "file_wizville")],
            limit=1,
        )
        if file_attachment:
            # file_path local
            file_path = self.env["ir.attachment"]._full_path(file_attachment.store_fname)
            with paramiko.Transport((sftp_host, int(sftp_port))) as transport:
                transport.connect(username=sftp_user, password=sftp_password)
                with paramiko.SFTPClient.from_transport(transport) as sftp:
                    # Récupération du répertoire distant
                    remote_file_path = ir_default_obj.get(
                        "of.connector.config.settings", "wizville_sftp_deposit_directory"
                    )
                    if not remote_file_path:
                        sftp.close()
                        return
                    remote_file_path = "%s/%s" % (remote_file_path, self.file_name_wizville)

                    # Upload du fichier présent dans file_path vers remote_file_path
                    sftp.put(file_path, remote_file_path)
                    self.write({"is_done": True})
                    sftp.close()

    @api.model
    def cron_do_export_wizville(self):
        files_to_deposit = self.search([("type", "=", "export"), ("is_done", "=", False)])
        for file_to_integrate in files_to_deposit:
            file_to_integrate.put_file_wizville()
        return True

    @api.model
    def cron_do_import_wizville(self, rename_file=True):
        self.get_file_wizville(rename_file=rename_file)
        files_to_integrate = self.search([("type", "=", "import"), ("is_done", "=", False)])
        for file_to_integrate in files_to_integrate:
            file_to_integrate.integrate_wizville_file()

    @api.model
    def get_file_wizville(self, rename_file=True):
        ir_default_obj = self.env["ir.default"]
        sftp_host = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_host")
        sftp_port = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_port")
        sftp_user = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_user")
        sftp_password = ir_default_obj.get("of.connector.config.settings", "wizville_sftp_password")
        import_filename = ir_default_obj.get("of.connector.config.settings", "wizville_import_filename")

        if not sftp_host or not sftp_port or not sftp_user or not sftp_password:
            return

        companies = self.env["res.company"].search([("of_wizville_code", "!=", False)])
        filenames = []
        for company in companies:
            new_filename = safe_eval(import_filename, {"company_code": company.of_wizville_code})
            if new_filename not in filenames:
                filenames.append(new_filename)
        if not filenames:
            filenames.append(safe_eval(import_filename))
        if not filenames:
            return
        new_history_vals = {"type": "import"}
        cr = self.env.cr
        with paramiko.Transport((sftp_host, int(sftp_port))) as transport:
            transport.connect(username=sftp_user, password=sftp_password)
            with paramiko.SFTPClient.from_transport(transport) as sftp:
                remoteDirectoryPath = ir_default_obj.get(
                    "of.connector.config.settings", "wizville_sftp_pickup_directory"
                )
                if not remoteDirectoryPath:
                    sftp.close()
                    return

                sftp.getcwd(remoteDirectoryPath)
                directory_structure = sftp.listdir_attr()
                potential_files = []
                for sftpattr in directory_structure:
                    if hasattr(sftpattr, "filename"):
                        filename = sftpattr.filename
                        if (
                            isinstance(filename, str)
                            and filename.endswith(".csv")
                            and not filename.endswith(".processed.csv")
                            and any(filename.startswith(filename_tested) for filename_tested in filenames)
                        ):
                            potential_files.append(filename)
                if potential_files:
                    for filename in potential_files:
                        fd, path = tempfile.mkstemp(prefix="wizville_data", suffix=".csv")
                        sftp.get("%s/%s" % (remoteDirectoryPath, filename), path)
                        try:
                            with open(path, "rb") as encode:
                                encoded_file = base64.b64encode(encode.read())
                        finally:
                            os.close(fd)
                            try:
                                os.remove(path)
                            except Exception:
                                _logger.exception("Error while removing file %s", path)
                        new_history_vals["file_name_wizville"] = filename
                        new_history_vals["file_wizville"] = encoded_file
                        self.create(new_history_vals)
                        if rename_file:
                            sftp.rename(
                                "%s/%s" % (remoteDirectoryPath, filename),
                                "%s/%s" % (remoteDirectoryPath, filename.replace(".csv", ".processed.csv")),
                            )
                        # Vu que l'on peut renommer le fichier il vaut mieux éviter qu'un rollback vienne supprimer
                        # les enregistrements déjà créés
                        cr.commit()
                sftp.close()

    def integrate_wizville_file(self):
        self.ensure_one()

    def _compute_encoding(self, file_enc):
        try:
            result = chardet.detect(file_enc)
            if result:
                file_encoding = result["encoding"]
                return file_encoding
            else:
                raise UserError(_("Encoding not recognized."))
        except Exception:
            raise UserError(_("Error: encoding not recognized."))

    def _read_csv(self):
        # Lecture du fichier d'import par la bibliothèque csv de python
        csv_data = base64.decodebytes(self.file_wizville)
        # Deviner automatiquement les paramètres : caractère séparateur, type de saut de ligne,...
        dialect = csv.Sniffer().sniff(csv_data)

        file_encoding = self._compute_encoding(csv_data)
        self.file_encoding = file_encoding

        # Encode en utf-8
        if file_encoding != "utf-8":
            csv_data = csv_data.decode(file_encoding).encode("utf-8")

        dialect.delimiter = ";"

        reader = csv.DictReader(StringIO(csv_data.decode("utf-8")), dialect=dialect)

        prems = True
        for row in reader:
            if prems:
                prems = False
                yield [item.strip() for item in reader.fieldnames]
            if not any(x for x in row if x.strip()):
                # Ligne vide
                continue
            yield {key.strip(): (value and value.strip() or "") for key, value in row.items()}
