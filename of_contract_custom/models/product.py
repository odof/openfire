# -*- coding: utf-8 -*-

from odoo import models, fields, api


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

