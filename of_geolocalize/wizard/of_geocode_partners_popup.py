# -*- coding: utf-8 -*-

from odoo import api, fields, models

class of_geocode_partners_popup(models.TransientModel):
    """
    wizard to either launch geocoding of partners using Nominatim or to go to non-geocodable partners in order to do it manually
    """
    _name = "of.geocode.partners.popup"

    mode = fields.Selection([
        ('not_tried',"Try to geocode all partners who haven't been tried yet, with the exception of partners manually localized. Use this mode on first attempt."),
        ('failure',"Try to geocode all partners not yet localized, using our greedier algorithm."),
        ('all_but_manual',"Try to geocode ALL partners, with the exception of partners manually localized. Use this mode with caution."),
        ('manual','Fetch partners who miss geolocation in order to do it manually.'),
        ], default='non_geocoded')

    @api.multi
    def resolve(self):
        company_ids = self._context['active_ids']
        if not company_ids:
            return
        company = self.env["res.company"].browse(company_ids[0])
        if self.mode == 'not_tried':
            company.geo_code_partners();
        elif self.mode == 'failure':
            company.geo_code_partners_retry();
        elif self.mode == 'all_but_manual':
            company.geo_code_partners_rewrite();
        elif self.mode == 'manual':
            return company.action_view_geocoding_failure();

        return True
