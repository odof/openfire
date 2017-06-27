# -*- coding: utf-8 -*-

from odoo import api, models, fields
import odoo.addons.decimal_precision as dp

class OfProductTemplate(models.Model):
    _inherit = "product.template"

class OfProductProduct(models.Model):
    _inherit = "product.product"

    modele = fields.Char(string='Modèle')
    marge = fields.Float(string='Marge',digits=2,compute="_compute_marge")
    date_tarif = fields.Date(string="Date du tarif")
    old_code = fields.Char(string="Ancienne Référence")

    @api.multi
    def _compute_marge(self):
        for product in self:
            product.marge = (product.lst_price - product.standard_price) * 100 / product.lst_price

    @api.model
    def _add_missing_default_values(self, values):
        # Mettre la référence produit (default_code) du template par défaut lors de la création d'une variante.
        if 'product_tmpl_id' in values and values['product_tmpl_id']:
            values['default_code'] = self.env['product.template'].browse(values['product_tmpl_id']).default_code
        return super(OfProductProduct, self)._add_missing_default_values(values)
