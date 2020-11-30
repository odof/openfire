# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_storage = fields.Boolean(string=u"Stockage et retrait à la demande")
