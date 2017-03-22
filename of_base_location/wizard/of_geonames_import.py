# -*- coding: utf-8 -*-

from odoo import api, models

class BetterZipGeonamesImport(models.TransientModel):
    _inherit = 'better.zip.geonames.import'

    @api.model
    def _prepare_better_zip(self, row, country):
        res = super(BetterZipGeonamesImport, self)._prepare_better_zip(row, country)
        res.update({
            'geo_lat': row[9],
            'geo_lng': row[10],
        })
        return res
