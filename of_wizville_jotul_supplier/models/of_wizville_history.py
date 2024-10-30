# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


try:
    from io import StringIO
except ImportError:
    from io import StringIO

import base64
import csv
import logging
import re
from collections import defaultdict

import dateutil.parser as dateutil_parser

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class OFWizvilleHistory(models.Model):
    _inherit = "of.wizville.history"

    def action_button_integrate_wizville_file(self):
        """Customize Wizville file integration for supplier Jotul."""
        self.ensure_one()

        try:
            possible_date = re.sub("[^0-9]", "", self.name)
            possible_date = dateutil_parser.parse(possible_date)
            date = possible_date.date()
        except ValueError:
            date = fields.Date.today()

        reader = self._read_csv()

        company_column_name = "Code_magasin"
        if company_column_name not in reader.fieldnames:
            _logger.error(
                "[WIZVILLE] : Missing required column '%s' in CSV file. Aborting import.", company_column_name
            )
            return

        files_to_create = defaultdict(list)
        for line in reader:
            try:
                files_to_create[line[company_column_name]].append(line)
            except KeyError:
                _logger.error(
                    "[WIZVILLE] : Couldn't find company column '%s' in row. Skipping row.", company_column_name
                )
                continue

        self._generate_new_exports_for_retailers(files_to_create, date)
        self.write({"is_export_done": True})

    @api.model
    def _generate_new_exports_for_retailers(self, vals, date):
        """
        Generates and encodes separate export files for each shop based on the parsed data.
        The filenames are generated dynamically using a format stored in the configuration settings.
        Args:
            vals (dict)
            date (datetime.date)
        Returns:
            dict
        """

        # Retrieve file naming format
        export_filename = self.env["ir.config_parameter"].sudo().get_param("of.wizville.base.wizville_export_filename")
        for company_code, values in vals.items():
            file_buffer = self._get_wizville_export_values(values)
            encoded_file_buffer = base64.b64encode(file_buffer.encode("utf-8", "ignore"))

            name = safe_eval(
                export_filename,
                {
                    "today": fields.Date.today().strftime("%Y-%m-%d"),
                    "company_code": company_code,
                    "date": date.strftime("%Y-%m-%d"),
                },
            )
            self.create(
                {
                    "file": encoded_file_buffer,
                    "name": name,
                    "type": "export",
                    "export_date": date,
                }
            )
        return vals

    @api.model
    def _get_wizville_export_values(self, values):
        """
        Generates a CSV string from a list of dictionaries.
        The columns are dynamically generated based on mandatory fields.

        Args:
            values (list): A list of dictionaries.

        Returns:
            str: A CSV-formatted string containing all rows of data, ready for encoding and exporting.
        """
        # Mandatory columns
        columns = [
            "Auteur",
            "ID_client",
            "Code_magasin",
            "Email",
            "Date_de_facturation",
            "Date",
        ]
        # Add question columns dynamically
        for line_value in values:
            for key in line_value:
                if key not in columns:
                    columns.append(key)
        file = StringIO()
        w = csv.writer(file, delimiter=";")
        w.writerow(columns)

        for line_value in values:
            w.writerow([line_value.get(col, "") for col in columns])

        return file.getvalue()
