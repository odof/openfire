# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_is_pou_product = fields.Boolean(compute='_compute_of_is_pou_product')
    of_pou_artas400 = fields.Char(string=u"Artas400")
    of_pou_variante = fields.Integer(string=u"Variante d'article")
    of_pou_cond = fields.Char(string=u"Unité de conditionnement")

    @api.depends('brand_id')
    def _compute_of_is_pou_product(self):
        poujoulat_brand_ids = self.env['ir.values'].get_default(
            'of.connector.config.settings', 'of_poujoulat_brand_ids') or []
        for record in self:
            if record.brand_id and record.brand_id.id in poujoulat_brand_ids:
                record.of_is_pou_product = True
