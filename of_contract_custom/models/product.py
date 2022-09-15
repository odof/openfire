# -*- coding: utf-8 -*-

# 1: imports of python lib
# 2: imports of odoo
from odoo import models, fields, api
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class OfProductTemplate(models.Model):
    _inherit = 'product.template'

    of_index_ids = fields.Many2many(
        comodel_name='of.index', string=u"Indice liés", compute='_compute_of_index_ids')
    of_product_index_ids = fields.Many2many(comodel_name='of.index', string=u"Indices liés à l'article")

    @api.depends('of_product_index_ids', 'categ_id', 'categ_id.of_index_ids')
    def _compute_of_index_ids(self):
        for product in self:
            indexes = product.of_product_index_ids
            indexes |= product.categ_id.of_index_ids
            product.of_index_ids = indexes


class ProductCategory(models.Model):
    _inherit = 'product.category'

    of_index_ids = fields.Many2many(comodel_name='of.index', string="Indices")

