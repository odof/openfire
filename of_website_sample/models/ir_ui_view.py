# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def render_template(self, template, values=None, engine='ir.qweb'):
        res = super(IrUiView, self).render_template(template, values, engine)
        if template in ['website_sale.cart', 'website_sale.cart_lines']:
            # On retire les readonly=0 pour les lignes de paniers non échantillon
            res = res.replace('readonly="0"', '')
        return res
