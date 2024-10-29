# -*- coding: utf-8 -*-


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import base64
import logging
from collections import defaultdict
import dateutil.parser as dparser
import re

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval
import csv

_logger = logging.getLogger(__name__)


class OFWizvilleHistory(models.Model):
    _inherit = 'of.wizville.history'

    @api.multi
    def integrate_wizville_file(self):
        self.ensure_one()
        try:
            # export date is in the filename, trying to get it
            possible_date = re.sub("[^0-9]", "", self.file_name_wizville)
            possible_date = dparser.parse(possible_date)
            date = fields.Date.to_string(possible_date)
        except ValueError:
            date = fields.Date.today()
        reader = self._read_csv()
        column_names = reader.next()  # just to skip first line
        company_column_name = 'Code_magasin'  # this should tell us which client the information goes to
        files_to_create = defaultdict(list)
        while True:
            try:
                line = reader.next()
            except StopIteration:
                break
            try:
                files_to_create[line[company_column_name]].append(line)
            except ValueError:
                _logger.error("[WIZVILLE] : Couldn't find company column. Aborting import.")
                return
        self._generate_new_exports_for_retailers(files_to_create, date)
        self.write({'done': True})

    @api.model
    def _generate_new_exports_for_retailers(self, vals, date):
        file_name_eval = self.env['ir.values'].get_default(
            'of.connector.config.settings', 'of_wizville_export_filename')
        for company_code, values in vals.iteritems():
            file_buffer = self._get_wizville_export_values(values)
            file_buffer = base64.encodestring(file_buffer.encode('utf-8', 'ignore'))
            name = safe_eval(file_name_eval, {'today': fields.Date.today(), 'company_code': company_code, 'date': date})
            self.create({
                'file_wizville': file_buffer,
                'file_name_wizville': name,
                'type': 'export',
                'date': date,
            })
        return vals

    @api.model
    def _get_wizville_export_values(self, values):
        # Colonnes obligatoires
        columns = [
            u"Auteur",
            u"ID_client",
            u"Code_magasin",
            u"Email",
            u"Date_de_facturation",
            u"Date",
        ]
        # Ajout colonnes de questions
        for line_value in values:
            for key in line_value:
                if key not in columns:
                    columns.append(key)
        file = StringIO()
        w = csv.writer(file, delimiter=';')
        w.writerow(columns)
        for line_value in values:
            new_line = [
                line_value.get(col, '').encode('utf-8')
                for col in columns
            ]
            w.writerow(new_line)
        value = file.getvalue()
        return value
