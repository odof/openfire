# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductSuppliferinfo(models.Model):
    _inherit = 'product.supplierinfo'

    of_product_type = fields.Selection(
        selection=[
                ('pellet', u"Pellet"),
                ('bois', u"Bois"),
                ('gaz', u"Gaz"),
                ('mixte', u"Mixte"),
            ],
        string=u"Type de l'appareil")
