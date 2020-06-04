# -*- coding: utf-8 -*-

from odoo import models, api


class OfComposeMail(models.TransientModel):
    _inherit = 'of.compose.mail'

    @api.model
    def _get_dict_values(self, o, objects):
        result = super(OfComposeMail, self)._get_dict_values(o, objects)

        order = objects['order']
        lines = order.order_line.filtered('of_article_principal')
        main_product = lines[:1].product_id
        result.update({
            'o_article_principal_ref': main_product.default_code or '',
            'o_article_principal_name': main_product.name or '',
            'o_article_principal_description': main_product.description_sale or '',
        })
        return result
