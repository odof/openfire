# -*- coding: utf8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_product_tasks_tmpl_ids = fields.One2many(
        comodel_name='of.project.task.template', inverse_name='product_tmpl_id', string=u"Tâches", copy=False)
