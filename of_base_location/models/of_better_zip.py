# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BetterZip(models.Model):
    _inherit = 'res.better.zip'

    geo_lat = fields.Float(string='Latitude', digits=(16, 5))
    geo_lng = fields.Float(string='Longitude', digits=(16, 5))

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Fonction inspirée de celle de product_product
        if not args:
            args = []
        if name and operator == 'ilike':
            tab = name.strip().split(' ')
            zips = self.search([('name', '=like', tab[0]+'%')])
            if zips:
                name = ' '.join(tab[1:])
            elif len(tab) > 1:
                zips = self.search([('name', '=like', tab[-1]+'%')])
                if zips:
                    name = ' '.join(tab[:-1])

            if zips:
                zips = self.search([('id', 'in', zips._ids), ('city', 'ilike', name)] + args)
                return zips.name_get()
        return super(BetterZip, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.one
    def _get_display_name(self):
        if self.country_id and self.country_id.code == 'FR':
            if self.name:
                name = [self.name, self.city]
            else:
                name = [self.city]
            self.display_name = ", ".join(name)
        else:
            super(BetterZip, self)._get_display_name()
