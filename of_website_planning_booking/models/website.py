# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class Website(models.Model):
    _inherit = 'website'

    website_booking_terms_file = fields.Binary(
        string=u"(OF) Fichier PDF des Conditions Générales de Vente", filename='website_booking_terms_filename',
        compute='_compute_website_booking_terms_file')
    website_booking_terms_filename = fields.Char(
        string=u"(OF) Nom du fichier PDF des Conditions Générales de Vente",
        compute='_compute_website_booking_terms_file')

    def _compute_website_booking_terms_file(self):
        company_dependent = self.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_company_dependent',
            company_id=self.env.user.company_id.sudo().id)
        for record in self:
            if company_dependent:
                company = self.env.user.company_id.sudo()
            else:
                company = record.company_id.sudo()
            record.website_booking_terms_file = company.of_website_booking_terms_file
            record.website_booking_terms_filename = company.of_website_booking_terms_filename

