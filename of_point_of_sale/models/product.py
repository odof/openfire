# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_pos_favorite = fields.Boolean(string=u"Favori POS")
