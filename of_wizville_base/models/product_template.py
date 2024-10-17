# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_product_type = fields.Selection(
        string=u"Type de l'appareil", related='seller_ids.of_product_type', readonly=False)
