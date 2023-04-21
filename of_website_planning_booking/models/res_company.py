# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_website_booking_terms_file = fields.Binary(
        string=u"(OF) Fichier PDF des Conditions Générales de Vente",
        filename='website_booking_terms_filename', attachment=True)
    of_website_booking_terms_filename = fields.Char(string=u"(OF) Nom du fichier PDF des Conditions Générales de Vente")

