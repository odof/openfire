# -*- coding: utf-8 -*-

import logging

from os import listdir, mkdir, rename
from os.path import isfile, join, exists, splitext

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OFArchive(models.Model):
    _name = 'of.archive'
    _description = "Archive OpenFlam"

    type_id = fields.Many2one(
        comodel_name='of.archive.type', string=u"Type d'archive", required=True,
        default=lambda self: self._get_default_type_id())
    number = fields.Char(string=u"Numéro", required=True)
    date = fields.Date(string=u"Date", required=True)
    amount_untaxed = fields.Float(string=u"Montant HT")
    amount_total = fields.Float(string=u"Montant TTC")
    display_amount_untaxed = fields.Boolean(related='type_id.display_amount_untaxed', string=u"Afficher le montant HT")
    display_amount_total = fields.Boolean(related='type_id.display_amount_untaxed', string=u"Afficher le montant TTC")
    document_pdf = fields.Binary(string=u"Document PDF")
    document_no_pdf = fields.Binary(string=u"Document non PDF")
    document_name = fields.Char(string=u"Nom du document")
    document_extension = fields.Char(string=u"Format du document")

    customer_type = fields.Selection(
        selection=[('int', u'Interne'), ('ext', u'Externe')], string=u"Type de client", required=True)

    # Informations clients internes
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Client interne", index=True)
    partner_ref = fields.Char(related='partner_id.ref', string=u"Numéro de client interne")
    partner_title = fields.Char(related='partner_id.title.name', string=u"Civilité du client interne")
    partner_street = fields.Char(related='partner_id.street', string=u"Adresse du client interne")
    partner_street2 = fields.Char(related='partner_id.street2', string=u"Adresse (suite) du client interne")
    partner_zip = fields.Char(related='partner_id.zip', string=u"Code postal du client interne")
    partner_city = fields.Char(related='partner_id.city', string=u"Ville du client interne")
    partner_country = fields.Char(related='partner_id.country_id.name', string=u"Pays du client interne")
    partner_phone = fields.Char(related='partner_id.phone', string=u"Téléphone du client interne")
    partner_mobile = fields.Char(related='partner_id.mobile', string=u"Mobile du client interne")
    partner_fax = fields.Char(related='partner_id.fax', string=u"Fax du client interne")
    partner_email = fields.Char(related='partner_id.email', string=u"Email du client interne")

    # Informations clients externes
    customer_name = fields.Char(string=u"Nom du client externe")
    customer_ref = fields.Char(string=u"Numéro de client externe", index=True)
    customer_title = fields.Char(string=u"Civilité du client externe")
    customer_street = fields.Char(string=u"Adresse du client externe")
    customer_street2 = fields.Char(string=u"Adresse (suite) du client externe")
    customer_zip = fields.Char(string=u"Code postal du client externe")
    customer_city = fields.Char(string=u"Ville du client externe")
    customer_country = fields.Char(string=u"Pays du client externe")
    customer_phone = fields.Char(string=u"Téléphone du client externe")
    customer_mobile = fields.Char(string=u"Mobile du client externe")
    customer_fax = fields.Char(string=u"Fax du client externe")
    customer_email = fields.Char(string=u"Email du client externe")

    # Gestion de l'affichage des infos client en vue liste
    customer_name_display = fields.Char(
        string=u"Nom du client à afficher", compute='_compute_customer_display_fields', search='_search_customer_name')
    customer_ref_display = fields.Char(
        string=u"Numéro de client client à afficher", compute='_compute_customer_display_fields',
        search='_search_customer_ref')
    customer_zip_display = fields.Char(
        string=u"Code postal du client à afficher", compute='_compute_customer_display_fields',
        search='_search_customer_zip')
    customer_city_display = fields.Char(
        string=u"Ville de client client à afficher", compute='_compute_customer_display_fields',
        search='_search_customer_city')

    @api.model
    def _get_default_type_id(self):
        default_type_id = self.env['of.archive.type'].search([('default_type', '=', True)], limit=1)
        if default_type_id:
            return default_type_id.id
        else:
            return self.env['of.archive.type'].search([], limit=1).id

    @api.multi
    def name_get(self):
        res = []
        for archive in self:
            name = "%s - %s" % (archive.type_id.name, archive.number)
            res.append((archive.id, name))
        return res

    @api.multi
    def _compute_customer_display_fields(self):
        for rec in self:
            if rec.customer_type == 'int':
                rec.customer_name_display = rec.partner_id.name
                rec.customer_ref_display = rec.partner_id.ref
                rec.customer_zip_display = rec.partner_id.zip
                rec.customer_city_display = rec.partner_id.city
            elif rec.customer_type == 'ext':
                rec.customer_name_display = rec.customer_name
                rec.customer_ref_display = rec.customer_ref
                rec.customer_zip_display = rec.customer_zip
                rec.customer_city_display = rec.customer_city

    def _search_customer_name(self, operator, value):
        return ['|', ('partner_id.name', operator, value), ('customer_name', operator, value)]

    def _search_customer_ref(self, operator, value):
        return ['|', ('partner_id.ref', operator, value), ('customer_ref', operator, value)]

    def _search_customer_zip(self, operator, value):
        return ['|', ('partner_id.zip', operator, value), ('customer_zip', operator, value)]

    def _search_customer_city(self, operator, value):
        return ['|', ('partner_id.city', operator, value), ('customer_city', operator, value)]


class OFArchiveType(models.Model):
    _name = 'of.archive.type'
    _description = "Type d'archive OpenFlam"

    name = fields.Char(string="Nom", required=True)
    display_amount_untaxed = fields.Boolean(string="Afficher le montant HT", default=True)
    display_amount_total = fields.Boolean(string="Afficher le montant TTC", default=True)
    default_type = fields.Boolean(string="Type par défaut")


class OFArchiveImport(models.Model):
    _name = 'of.archive.import'
    _description = "Import des archives OpenFlam"

    state = fields.Selection(selection=[('draft', 'Brouillon'),
                                        ('done', 'Terminé')],
                             string="Statut", default='draft', readonly=True)
    name = fields.Char(string="Nom", required=True)
    dir_path = fields.Char(string="Dossier source", default="/home/odoo/archive/", required=True)
    extension = fields.Char(string="Extension des fichiers", default=".pdf", help=".pdf, .xls, .txt, .csv, ...",
                            required=True)
    date = fields.Date(string="Date", readonly=True)

    import_message_ids = fields.One2many(comodel_name='of.archive.import.message', inverse_name='import_id',
                                         string="Messages")
    import_error_ids = fields.One2many(comodel_name='of.archive.import.message', inverse_name='import_id',
                                       string="Erreurs", domain=[('type', '=', 'error')], readonly=True)
    import_warning_ids = fields.One2many(comodel_name='of.archive.import.message', inverse_name='import_id',
                                         string="Avertissements", domain=[('type', '=', 'warning')], readonly=True)
    import_info_ids = fields.One2many(comodel_name='of.archive.import.message', inverse_name='import_id',
                                      string="Infos", domain=[('type', '=', 'info')], readonly=True)

    @api.multi
    def run_import(self):
        self.ensure_one()
        _logger.info("Archive import - START")
        files = []
        if self.dir_path:
            # Ajout d'un slash à la fin si manquant
            directory = join(self.dir_path, '')
            # Parcours du répertoire pour lister les fichiers présents
            if exists(directory):
                for file_name in listdir(directory):
                    file_full_path = join(directory, file_name)
                    if isfile(file_full_path) and file_name[0] != '.':
                        filename_wo_ext, file_extension = splitext(file_name)
                        if file_extension == self.extension:
                            files.append([file_name, file_full_path, filename_wo_ext])
            else:
                _logger.info("Archive import - ERREUR : Répertoire inexistant !")
                self.write({'date': fields.Date.today(),
                            'state': 'done',
                            'import_error_ids': [(0, 0, {'type': 'error',
                                                         'message': "Répertoire spécifié inexistant !"})]})
                _logger.info("Archive import - END")
                return True
        if files:
            ok_directory = join(directory[:-1] + '_ok', '')
            files_to_move = []
            # Parcours des fichiers trouvés pour les lier aux archives
            for file in files:
                archive = self.env['of.archive'].search([('number', '=', file[2])])
                if archive:
                    if self.extension == '.pdf':
                        archive.write({'document_pdf': open(file[1], 'rb').read().encode('base64'),
                                       'document_name': filename_wo_ext + self.extension,
                                       'document_extension': self.extension})
                    else:
                        archive.write({'document_no_pdf': open(file[1], 'rb').read().encode('base64'),
                                       'document_name': filename_wo_ext + self.extension,
                                       'document_extension': self.extension})
                    _logger.info("Archive import - Import OK for file %s" % file[0])

                    # On stocke les informations pour déplacer le fichier en fin de traitement
                    # On teste si le fichier n'existe pas déjà
                    dest_file_full_path = ok_directory + file[0]
                    if exists(dest_file_full_path):
                        i = 1
                        dest_file_full_path = ok_directory + file[2] + '_' + str(i) + self.extension
                        while exists(dest_file_full_path):
                            i += 1
                            dest_file_full_path = ok_directory + file[2] + '_' + str(i) + self.extension
                    files_to_move.append((file[1], dest_file_full_path))

                    self.write({'import_info_ids': [(0, 0, {'type': 'info',
                                                            'message': "Le fichier %s a été lié à l'archive %s" %
                                                                       (file[0], file[2])})]})
                else:
                    self.write({'import_warning_ids': [(0, 0, {'type': 'warning',
                                                               'message': "Aucune archive trouvée correspondant au "
                                                                          "fichier %s" % file[0]})]})

            # Création du répertoire ok s'il n'existe pas
            if not exists(ok_directory):
                mkdir(ok_directory)
            # Déplacement des fichiers vers le répertoire _ok
            for move_info in files_to_move:
                rename(move_info[0], move_info[1])

        else:
            _logger.info("Archive import - ERREUR : Aucun fichier trouvé !")
            self.write({'import_error_ids': [(0, 0, {'type': 'error',
                                                     'message': "Aucun fichier trouvé dans le répertoire "
                                                                          "spécifié !"})]})

        self.write({'date': fields.Date.today(),
                    'state': 'done'})
        _logger.info("Archive import - END")
        return True

    @api.multi
    def set_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
        return True


class OFArchiveImportMessage(models.Model):
    _name = 'of.archive.import.message'
    _description = "Avertissement lors de l'import des archives OpenFlam"

    import_id = fields.Many2one(comodel_name='of.archive.import', string="Import", ondelete='cascade')
    type = fields.Selection(selection=[('error', 'Erreur'), ('warning', 'Avertissement'), ('info', 'Info')],
                            string="Type de message")
    date = fields.Datetime(string="Date", default=lambda self: fields.Datetime.now())
    message = fields.Text(string="Message")
