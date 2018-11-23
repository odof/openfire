# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _

import odoo.addons.decimal_precision as dp

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ecotax_amount = fields.Float(string="Ecotax amount", digits=dp.get_precision('Product Price'),
                                 help="Ecotax amount included in sale price")
