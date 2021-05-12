# -*- coding: utf-8 -*-

from odoo import api, models, fields


class Website(models.Model):
    _inherit = 'website'

    website_booking_terms_file = fields.Binary(
        string=u"(OF) Fichier PDF des Conditions Générales de Vente", filename='website_booking_terms_filename',
        attachment=True)
    website_booking_terms_filename = fields.Char(string=u"(OF) Nom du fichier PDF des Conditions Générales de Vente")
