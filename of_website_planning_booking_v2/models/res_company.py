# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_booking_terms_file = fields.Binary(
        string=u"Fichier PDF des Conditions Générales de Vente pour la prise de RDV en ligne",
        filename='of_booking_terms_filename', attachment=True)
    of_booking_terms_filename = fields.Char(
        string=u"Nom du fichier PDF des Conditions Générales de Vente pour la prise de RDV en ligne")
