# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_nbr_pallets = fields.Integer(string="Nbr. of pallets")
