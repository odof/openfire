# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import csv
import datetime
import itertools
import logging
from io import BytesIO, StringIO

from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _

logger = logging.getLogger(__name__)
try:
    import chardet
except ImportError:
    chardet = None

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import openpyxl
    from openpyxl.cell.cell import ERROR_CODES, NUMERIC_TYPES, TIME_TYPES

except ImportError:
    openpyxl = None


def compute_discount(*discounts):
    result = 100
    for discount in discounts:
        result *= (100 - discount) / 100.0
    return 100 - result


def _compute_encoding(file_enc):
    try:
        if result := chardet.detect(file_enc):
            return result['encoding']
        else:
            raise UserError("Encoding not recognized")
    except Exception as e:
        raise UserError("Error : encoding not recognized") from e


# --- READERS ---
# Un reader retourne au premier appel la liste des champs du fichier (éléments de la première ligne)
# Aux appels suivants, le reader retourne un dictionnaire {nom de la colonne: valeur} pour la ligne suivante


def _read_csv(file, separator=None):
    # Lecture du fichier d'import par la bibliothèque csv de python
    csv_data = base64.decodestring(file)
    # Deviner automatiquement les paramètres : caractère séparateur, type de saut de ligne,...
    dialect = csv.Sniffer().sniff(csv_data)
    file_encoding = _compute_encoding(csv_data)

    # Encode en utf-8
    if file_encoding != 'utf-8':
        csv_data = csv_data.decode(file_encoding).encode('utf-8')

    if separator and separator.strip(' '):
        dialect.delimiter = separator.strip(' ').replace('\\t', '\t')

    reader = csv.DictReader(StringIO(csv_data), dialect=dialect)

    first = True
    for row in reader:
        if first:
            first = False
            yield [item.strip().decode('utf8', 'ignore') for item in row]
        if not any(x for x in row if x.strip()):
            # Ligne vide
            continue
        yield {
            key.strip().decode('utf8', 'ignore'): value.strip().decode('utf8', 'ignore')
            for key, value in row.iteritems()
        }


# MS OFFICE
def _read_xls(file):
    """Read file content, using xlrd lib"""
    book = xlrd.open_workbook(file_contents=base64.b64decode(file))
    sheet = book.sheet_by_index(0)
    header = False
    # emulate Sheet.get_rows for pre-0.9.4
    for row in itertools.imap(sheet.row, range(sheet.nrows)):
        values = []
        for cell in row:
            if cell.ctype is xlrd.XL_CELL_NUMBER:
                is_float = cell.value % 1 != 0.0
                values.append(cell.value if is_float else int(cell.value))
            elif cell.ctype is xlrd.XL_CELL_DATE:
                is_datetime = cell.value % 1 != 0.0
                # emulate xldate_as_datetime for pre-0.9.3
                dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                values.append(
                    dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if is_datetime
                    else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                )
            elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                values.append('True' if cell.value else 'False')
            elif cell.ctype is xlrd.XL_CELL_ERROR:
                raise ValueError(
                    _("Error cell found while reading XLS/XLSX file: %s")
                    % xlrd.error_text_from_code.get(cell.value, "unknown error code %s" % cell.value)
                )
            else:
                values.append(cell.value.strip())
        if any(values):
            if header:
                yield {header[i]: values[i] for i in range(len(header))}
            else:
                header = values
                yield header


def _read_xlsx(file):
    """Read file content, using openpyxl lib"""
    filedata = BytesIO(base64.b64decode(file))
    book = openpyxl.load_workbook(filedata)
    sheet = book.worksheets[0]
    header = False

    for row in sheet.iter_rows(values_only=True):
        values = []
        logger.info(row)
        for cell in row:
            if isinstance(cell, NUMERIC_TYPES):
                values.append(cell)
            elif isinstance(cell, TIME_TYPES):
                is_datetime = isinstance(cell, datetime.datetime)
                values.append(
                    cell.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if is_datetime
                    else cell.strftime(DEFAULT_SERVER_DATE_FORMAT)
                )
            elif isinstance(cell, bool):
                values.append('True' if cell else 'False')
            elif cell in ERROR_CODES:
                raise ValueError(_(f"Error cell found while reading XLSX file: {cell}"))
            else:
                values.append(cell.strip() if cell else '')
        if any(values):
            if header:
                yield {header[i]: values[i] for i in range(len(header))}
            else:
                header = values
                yield values


def _get_odoo_fields_attachment():
    return {
        'name': {
            'description': "Label",
            'required': True,
            'type': 'char',
            'lang': False,
            'translate': False,
        },
        'store_fname': {
            'description': "Filepath",
            'required': True,
            'type': 'char',
            'lang': False,
            'translate': False,
        },
        'res_model': {
            'description': "Model",
            'required': True,
            'type': 'char',
            'lang': False,
            'translate': False,
        },
        'res_id': {
            'description': "Product reference",
            'required': True,
            'type': 'char',
            'lang': False,
            'translate': False,
        },
        'res_field': {
            'description': "Field (or empty if attachement)",
            'required': False,
            'type': 'char',
            'lang': False,
            'translate': False,
        },
    }
