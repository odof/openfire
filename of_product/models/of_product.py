# -*- coding: utf-8 -*-

from odoo import api, models, fields
import odoo.addons.decimal_precision as dp

class OfProductTemplate(models.Model):
    _inherit = "product.template"

    modele = fields.Char(string='Modèle')
    marge = fields.Float(string='Marge',digits=(4,2),compute="_compute_marge",
                help="Marge calculée sur base du prix de vente")
    description_fabricant = fields.Text('Description du fabricant', translate=True)
    date_tarif = fields.Date(string="Date du tarif")

    @api.multi
    @api.depends('lst_price','standard_price')
    def _compute_marge(self):
        # la marge est calculée en fonction du prix de vente, faire en fonction du prix d'achat?
        for product in self:
            lst_price = product.lst_price
            if lst_price != 0:
                product.marge = (lst_price - product.standard_price) * 100.00 / lst_price
            else: # division par 0!
                product.marge = -100

class OfProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _add_missing_default_values(self, values):
        # Mettre la référence produit (default_code) du template par défaut lors de la création d'une variante.
        if 'product_tmpl_id' in values and values['product_tmpl_id']:
            values['default_code'] = self.env['product.template'].browse(values['product_tmpl_id']).default_code
        return super(OfProductProduct, self)._add_missing_default_values(values)

class OFSuppliferInfo(models.Model):
    _inherit = "product.supplierinfo"

    old_code = fields.Char(string="Ancienne Référence")
    pp_ht = fields.Float(string='Prix public HT', default=1.0, digits=dp.get_precision('Product Price'),
        required=True, help="Prix Public HT conseillé par le fabricant")
    pp_currency_id = fields.Many2one(related='currency_id')
    remise = fields.Float(string='Remise',digits=(4,2),compute="_compute_remise")

    @api.multi
    @api.depends('pp_ht','price')
    def _compute_remise(self):
        for supinfo in self:
            pp_ht = supinfo.pp_ht
            if pp_ht != 0:
                supinfo.remise = (pp_ht - supinfo.price) * 100.00 / pp_ht
            else: # division par 0!
                supinfo.remise = -100
