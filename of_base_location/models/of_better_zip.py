# -*- coding: utf-8 -*-

from odoo import models, fields

class BetterZip(models.Model):
    _inherit = 'res.better.zip'

    geo_lat = fields.Float(string='Latitude', digits=(16, 5))
    geo_lng = fields.Float(string='Longitude', digits=(16, 5))
