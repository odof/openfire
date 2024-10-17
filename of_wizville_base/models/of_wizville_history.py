# -*- coding: utf-8 -*-

import base64
import csv

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import chardet
except ImportError:
    chardet = None

import logging
import os
import pysftp
import tempfile

_logger = logging.getLogger(__name__)


class OfWizvilleHistory(models.Model):
    _name = 'of.wizville.history'
    _order = 'date'

    name = fields.Char(string=u"Nom", related='file_name_wizville', readonly=True)
    type = fields.Selection(
        [
            ('import', u"Import"),
            ('export', u"Export"),
        ], string='Export/Import', required=True)
    file_name_wizville = fields.Char(string=u"Nom du fichier wizville", size=100)
    file_wizville = fields.Binary(string=u"Fichier wizville", attachment=True)
    done = fields.Boolean(string=u"Export réalisé")
    date = fields.Date(string=u"Date de l'export", default=fields.Date.today())

    @api.multi
    def put_file_wizville(self):
        self.ensure_one()
        sftp_host = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_host')
        sftp_port = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_port')
        sftp_user = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_user')
        sftp_password = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_password')

        if not sftp_host or not sftp_port or not sftp_user or not sftp_password:
            return

        file_attachment = self.env['ir.attachment'].search(
            [
                ('res_model', '=', 'of.wizville.history'), ('res_id', '=', self.id),
                ('res_field', '=', 'file_wizville')
            ], limit=1)
        if file_attachment:
            # file_path local
            file_path = self.env['ir.attachment']._full_path(file_attachment.store_fname)
            cnopts = pysftp.CnOpts()
            # cnopts.hostkeys = None  # for tests only
            with pysftp.Connection(
                host=sftp_host, username=sftp_user, password=sftp_password, port=int(sftp_port), cnopts=cnopts
            ) as sftp:
                # file_path in sftp
                remote_file_path = self.env['ir.values'].get_default(
                    'of.connector.config.settings', 'of_wizville_sftp_deposit_directory')
                if not remote_file_path:
                    sftp.close()
                    return
                remote_file_path = '%s/%s' % (remote_file_path, self.file_name_wizville)

                # Upload du fichier présent dans file_path vers remote_file_path
                sftp.put(file_path, remote_file_path)
                self.write({'done': True})
                sftp.close()

    @api.model
    def do_export_wizville(self):
        files_to_deposit = self.search([('type', '=', 'export'), ('done', '=', False)])
        for file_to_integrate in files_to_deposit:
            file_to_integrate.put_file_wizville()
        return True

    @api.model
    def do_import_wizville(self, rename_file=True):
        self.get_file_wizville(rename_file=rename_file)
        files_to_integrate = self.search([('type', '=', 'import'), ('done', '=', False)])
        for file_to_integrate in files_to_integrate:
            file_to_integrate.integrate_wizville_file()

    @api.model
    def get_file_wizville(self, rename_file=True):
        sftp_host = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_host')
        sftp_port = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_port')
        sftp_user = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_user')
        sftp_password = self.env['ir.values'].get_default('of.connector.config.settings', 'of_wizville_sftp_password')
        import_filename = self.env['ir.values'].get_default(
            'of.connector.config.settings', 'of_wizville_import_filename')

        if not sftp_host or not sftp_port or not sftp_user or not sftp_password:
            return

        companies = self.env['res.company'].search([('of_wizville_code', '!=', False)])
        filenames = []
        for company in companies:
            new_filename = safe_eval(import_filename, {'company_code': company.of_wizville_code})
            if new_filename not in filenames:
                filenames.append(new_filename)
        if not filenames:
            filenames.append(safe_eval(import_filename))
        if not filenames:
            return
        cnopts = pysftp.CnOpts()
        # cnopts.hostkeys = None  # for tests only
        new_history_vals = {'type': 'import'}
        cr = self.env.cr
        with pysftp.Connection(
            host=sftp_host, username=sftp_user, password=sftp_password, port=int(sftp_port), cnopts=cnopts
        ) as sftp:
            remoteDirectoryPath = self.env['ir.values'].get_default(
                'of.connector.config.settings', 'of_wizville_sftp_pickup_directory')
            if not remoteDirectoryPath:
                sftp.close()
                return
            sftp.cwd(remoteDirectoryPath)
            directory_structure = sftp.listdir_attr()
            potential_files = []
            for sftpattr in directory_structure:
                if hasattr(sftpattr, 'filename'):
                    filename = sftpattr.filename
                    if (
                        isinstance(filename, basestring)
                        and filename.endswith('.csv')
                        and not filename.endswith('.processed.csv')
                        and any(filename.startswith(filename_tested) for filename_tested in filenames)
                    ):
                        potential_files.append(filename)
            if potential_files:
                for filename in potential_files:
                    fd, path = tempfile.mkstemp(prefix='wizville_data', suffix='.csv')
                    sftp.get('%s/%s' % (remoteDirectoryPath, filename), path)
                    try:
                        with open(path, "rb") as encode:
                            encoded_file = base64.b64encode(encode.read())
                    finally:
                        os.close(fd)
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                    new_history_vals['file_name_wizville'] = filename
                    new_history_vals['file_wizville'] = encoded_file
                    self.create(new_history_vals)
                    if rename_file:
                        sftp.rename('%s/%s' % (remoteDirectoryPath, filename),
                                    '%s/%s' % (remoteDirectoryPath, filename.replace('.csv', '.processed.csv')))
                    # Vu que l'on peut renommer le fichier il vaut mieux éviter qu'un rollback vienne supprimer
                    # les enregistrements déjà créés
                    cr.commit()
            sftp.close()

    @api.multi
    def integrate_wizville_file(self):
        self.ensure_one()

    @api.multi
    def _compute_encoding(self, file_enc):
        try:
            result = chardet.detect(file_enc)
            if result:
                file_encoding = result['encoding']
                return file_encoding
            else:
                raise UserError(u'Encodage non reconnu.')
        except Exception:
            raise UserError(u'Erreur : encodage non reconnu.')

    @api.multi
    def _read_csv(self):
        # Lecture du fichier d'import par la bibliothèque csv de python
        csv_data = base64.decodestring(self.file_wizville)
        # Deviner automatiquement les paramètres : caractère séparateur, type de saut de ligne,...
        dialect = csv.Sniffer().sniff(csv_data)

        file_encoding = self._compute_encoding(csv_data)
        self.file_encoding = file_encoding

        # Encode en utf-8
        if file_encoding != 'utf-8':
            csv_data = csv_data.decode(file_encoding).encode('utf-8')

        dialect.delimiter = ';'

        reader = csv.DictReader(
            StringIO(csv_data),
            dialect=dialect)

        prems = True
        for row in reader:
            if prems:
                prems = False
                yield [item.strip().decode('utf8', 'ignore') for item in reader.fieldnames]
            if not any(x for x in row if x.strip()):
                # Ligne vide
                continue
            yield {
                key.strip().decode('utf8', 'ignore'): value and value.strip().decode('utf8', 'ignore') or ""
                for key, value in row.iteritems()
            }
