# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFConnectorConfigSettings(models.TransientModel):
    _inherit = 'of.connector.config.settings'

    of_wizville_sftp_host = fields.Char(string=u"Adresse du serveur FTP")
    of_wizville_sftp_port = fields.Char(string=u"Port du serveur FTP")
    of_wizville_sftp_user = fields.Char(string=u"Identifiant")
    of_wizville_sftp_password = fields.Char(string=u"Mot de passe")
    of_wizville_sftp_deposit_directory = fields.Char(
        string=u"Dossier de dépôt des fichiers générés",
        help=u"Correspond à l'emplacement où les fichiers générés par OpenFire "
             u"doivent être déposés sur le sftp Wizville")
    of_wizville_sftp_pickup_directory = fields.Char(
        string=u"Dossier des fichiers de score",
        help=u"Correspond à l'emplacement où les fichiers générés par Wizville doivent être récupérés")
    of_wizville_export_filename = fields.Char(string=u"Nom du fichier d'export")
    of_wizville_import_filename = fields.Char(string=u"Nom du fichier d'import")
    of_wizville_satisfaction_question = fields.Integer(string=u"N° question pour \"Satisfaction globale\"")
    of_wizville_nps_pose_score_question = fields.Integer(string=u"N° question pour \"Score NPS\"")

    @api.multi
    def set_of_wizville_sftp_host_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_sftp_host', self.of_wizville_sftp_host)

    @api.multi
    def set_of_wizville_sftp_port_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_sftp_port', self.of_wizville_sftp_port)

    @api.multi
    def set_of_wizville_sftp_user_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_sftp_user', self.of_wizville_sftp_user)

    @api.multi
    def set_of_wizville_sftp_password_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_sftp_password', self.of_wizville_sftp_password)

    @api.multi
    def set_of_wizville_sftp_deposit_directory_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_sftp_deposit_directory',
            self.of_wizville_sftp_deposit_directory)

    @api.multi
    def set_of_wizville_sftp_pickup_directory_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_sftp_pickup_directory', self.of_wizville_sftp_pickup_directory)

    @api.multi
    def set_of_wizville_export_filename_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_export_filename', self.of_wizville_export_filename)

    @api.multi
    def set_of_wizville_import_filename_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_import_filename', self.of_wizville_import_filename)

    @api.multi
    def set_of_wizville_satisfaction_question_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_satisfaction_question',
            self.of_wizville_satisfaction_question)

    @api.multi
    def set_of_wizville_nps_pose_score_question_defaults(self):
        self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_wizville_nps_pose_score_question',
            self.of_wizville_nps_pose_score_question)
