# -*- coding: utf-8 -*-

from openerp import models, fields
import openerp.addons.decimal_precision as dp

class product_product(models.Model):
    _inherit = "product.product"

    of_frais_port = fields.Float(string='Frais de port', digits_compute=dp.get_precision('Product Price'), help="Frais de port")
