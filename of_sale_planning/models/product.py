# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_duration_per_unit = fields.Float(string=u"Durée")
