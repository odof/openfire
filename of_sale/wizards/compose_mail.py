# -*- coding: utf-8 -*-

from odoo import models, api

class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_dict_values(self, o, objects=None):
        if not objects:
            objects = self._get_objects(o)
        result = super(OfComposeMail,self)._get_dict_values(o, objects=objects)

        order = objects.get('order')
        lines = order and order.order_line.filtered('of_article_principal') or False
        main_product = lines and lines[0].product_id or False
        result.update({
            'o_article_principal_ref' : main_product and main_product.default_code or '',
            'o_article_principal_name' : main_product and main_product.name or '',
            'o_article_principal_description' : main_product and main_product.description_sale or '',
        })
        return result
