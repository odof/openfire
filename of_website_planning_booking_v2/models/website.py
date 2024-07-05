# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class Website(models.Model):
    _inherit = 'website'

    of_booking_terms_file = fields.Binary(
        string=u"Fichier PDF des Conditions Générales de Vente", filename='of_booking_terms_filename',
        compute='_compute_of_booking_terms_file')
    of_booking_terms_filename = fields.Char(
        string=u"Nom du fichier PDF des Conditions Générales de Vente",
        compute='_compute_of_booking_terms_file')

    def _compute_of_booking_terms_file(self):
        company_dependent = self.env['ir.values'].sudo().get_default(
            'of.intervention.settings', 'booking_company_dependent',
            company_id=self.env.user.company_id.sudo().id)
        for record in self:
            if company_dependent:
                company = self.env.user.company_id.sudo()
            else:
                company = record.company_id.sudo()
            record.of_booking_terms_file = company.of_booking_terms_file
            record.of_booking_terms_filename = company.of_booking_terms_filename
