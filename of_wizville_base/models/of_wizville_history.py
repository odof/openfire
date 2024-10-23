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
    _order = "export_date"

    name = fields.Char(string="Filename", size=100)
    file = fields.Binary()
    type = fields.Selection(
        selection=[
            ("import", "Import"),
            ("export", "Export"),
        ],
        string="Export/Import",
        required=True,
    )
    is_export_done = fields.Boolean(string="Export done")
    export_date = fields.Date(default=fields.Date.today())

    # -----------------------------------------------------------------------
    # Action methods
    # -----------------------------------------------------------------------

    def action_button_integrate_wizville_file(self):
        """That's the base function to integrate a file from Wizville.
        This function should be override in children modules to specify a custom integration process.
        """
        self.ensure_one()
        return True

    def action_button_put_file_wizville(self):
        self.ensure_one()
        if file_attachment := self.env["ir.attachment"].search(
            [
                ("res_model", "=", "of.wizville.history"),
                ("res_id", "=", self.id),
                ("res_field", "=", "file"),
            ],
            limit=1,
        ):
            ICP_obj = self.env["ir.config_parameter"].sudo()

            # get the file path from the store_fname
            file_path = self.env["ir.attachment"]._full_path(file_attachment.store_fname)
            try:
                with self._get_sftp_connection() as sftp:
                    # Récupération du répertoire distant
                    remote_filepath = ICP_obj.get_param("of.wizville.base.wizville_sftp_deposit_directory")
                    if not remote_filepath:
                        sftp.close()
                        return
                    remote_filepath = f"{remote_filepath}/{self.name}"

                    # Upload du fichier présent dans file_path vers remote_file_path
                    sftp.put(file_path, remote_filepath)
                    self.write({"is_export_done": True})
            except Exception as e:
                _logger.error("Failed to upload file to SFTP: %s", e)
                raise UserError(_("Failed to upload file to SFTP: %s") % e) from e

    # -----------------------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------------------

    @api.model
    def cron_do_export_wizville(self):
        """
        Cron job to export files to Wizville.

        It looks for records with type 'export' and 'is_export_done' set to False.
        For each file found, it calls the `put_file_wizville` method to handle the export.

        Returns:
            bool: Always returns True.
        """
        for file_to_integrate in self.search([("type", "=", "export"), ("is_export_done", "=", False)]):
            file_to_integrate.put_file_wizville()
        return True

    @api.model
    def cron_do_import_wizville(self, rename_file=True):
        self.get_file_wizville(rename_file=rename_file)
        for file_to_integrate in self.search([("type", "=", "import"), ("is_export_done", "=", False)]):
            file_to_integrate.action_button_integrate_wizville_file()

    def _get_sftp_config(self):
        ir_config_parameter_obj = self.env["ir.config_parameter"].sudo()
        sftp_host = ir_config_parameter_obj.get_param("of.wizville.base.wizville_sftp_host")
        sftp_port = ir_config_parameter_obj.get_param("of.wizville.base.wizville_sftp_port")
        sftp_user = ir_config_parameter_obj.get_param("of.wizville.base.wizville_sftp_user")
        sftp_password = ir_config_parameter_obj.get_param("of.wizville.base.wizville_sftp_password")
        return sftp_host, sftp_port, sftp_user, sftp_password

    def _get_sftp_connection(self):
        """Establishes and returns an SFTP connection based on configuration settings."""
        sftp_host, sftp_port, sftp_user, sftp_password = self._get_sftp_config()

        if not all([sftp_host, sftp_port, sftp_user, sftp_password]):
            raise UserError(_("Missing SFTP configuration settings."))

        transport = paramiko.Transport((sftp_host, int(sftp_port)))
        transport.connect(username=sftp_user, password=sftp_password)
        return paramiko.SFTPClient.from_transport(transport)

    def _get_filenames_to_retrieve(self):
        """Generates and returns a list of filenames expected on the SFTP server for download.

        Returns:
            list: List of filenames to retrieve.
        """
        import_filename = self.env["ir.config_parameter"].get_param("of.wizville.base.wizville_import_filename")

        companies = self.env["res.company"].search([("of_wizville_code", "!=", False)])
        filenames = []
        for company in companies:
            filename = safe_eval(import_filename, {"company_code": company.of_wizville_code})
            if filename not in filenames:
                filenames.append(filename)

        if not filenames:
            filenames.append(safe_eval(import_filename))

        return filenames

    def _download_and_process_files(self, sftp, filenames, remote_directory, rename_file=True):
        """Downloads and processes matching files from the SFTP directory."""
        potential_files = []

        sftp.getcwd(remote_directory)

        for sftpattr in sftp.listdir_attr():
            if hasattr(sftpattr, "filename"):
                filename = sftpattr.filename
                if (
                    filename.endswith(".csv")
                    and not filename.endswith(".processed.csv")
                    and any(filename.startswith(name) for name in filenames)
                ):
                    potential_files.append(filename)

        if potential_files:
            for filename in potential_files:
                fd, path = tempfile.mkstemp(prefix="wizville_data", suffix=".csv")
                try:
                    sftp.get(f"{remote_directory}/{filename}", path)
                    with open(path, "rb") as file_data:
                        encoded_file = base64.b64encode(file_data.read())
                finally:
                    os.close(fd)
                    try:
                        os.remove(path)
                    except Exception:
                        _logger.exception("Error while removing file %s", path)

                # Store in history
                self.create({"type": "import", "name": filename, "file": encoded_file})
                if rename_file:
                    sftp.rename(
                        f"{remote_directory}/{filename}",
                        f"{remote_directory}/{filename.replace('.csv', '.processed.csv')}",
                    )

                # Commit to avoid rollback issues on renamed files
                self.env.cr.commit()  # pylint: disable=E8102

    @api.model
    def get_file_wizville(self, rename_file=True):
        """Fetches files from SFTP, stores them in history, and optionally renames them as processed."""

        with self._get_sftp_connection() as sftp:
            filenames = self._get_filenames_to_retrieve()
            remote_directory = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("res.config.settings", "wizville_sftp_pickup_directory")
            )
            if not remote_directory:
                sftp.close()
                return

            self._download_and_process_files(sftp, filenames, remote_directory, rename_file=rename_file)

    def _get_file_encoding(self, file_enc):
        try:
            if result := chardet.detect(file_enc):
                return result["encoding"]
            else:
                raise UserError(_("Encoding not recognized."))
        except Exception as e:
            raise UserError(_("Error: encoding not recognized.")) from e

    def _read_csv(self):
        """
        Reads and processes a CSV file.

        This method decodes the base64-encoded CSV file, detects the CSV dialect,
        and reads the CSV data using Python's csv library. It handles different
        file encodings by converting them to UTF-8 and processes each row of the
        CSV file.

        Yields:
            list: The first row containing the field names, with leading and trailing
                whitespace removed.
            dict: Each subsequent row as a dictionary with keys as field names and
                values as the corresponding row values, with leading and trailing
                whitespace removed. Empty rows are skipped.
        """
        # Lecture du fichier d'import par la bibliothèque csv de python
        csv_data = base64.decodebytes(self.file)
        if not csv_data:
            raise UserError(_("No data found in the file."))

        # Deviner automatiquement les paramètres : caractère séparateur, type de saut de ligne,...
        dialect = csv.Sniffer().sniff(csv_data)

        self.file_encoding = self._get_file_encoding(csv_data)

        # Encode en utf-8
        if self.file_encoding != "utf-8":
            csv_data = csv_data.decode(self.file_encoding).encode("utf-8")

        dialect.delimiter = ";"

        reader = csv.DictReader(StringIO(csv_data.decode("utf-8")), dialect=dialect)

        first_call = True
        for row in reader:
            if first_call:
                first_call = False
                yield [item.strip() for item in reader.fieldnames]
            if not any(x for x in row if x.strip()):
                # Ligne vide
                continue
            yield {key.strip(): (value and value.strip() or "") for key, value in row.items()}
