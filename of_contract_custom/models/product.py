# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfProductTemplate(models.Model):
    _inherit = 'product.template'

    of_index_ids = fields.Many2many(
        comodel_name='of.index', string="Indice", related='categ_id.of_index_ids', readonly=True)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    of_index_ids = fields.Many2many(comodel_name='of.index', string="Indices")

