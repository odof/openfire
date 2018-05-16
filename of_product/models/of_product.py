# -*- coding: utf-8 -*-

from odoo import api, models, fields
import odoo.addons.decimal_precision as dp

class ProductTemplate(models.Model):
    _inherit = "product.template"

    modele = fields.Char(string='Modèle')
    marge = fields.Float(string='Marge', digits=(4, 2), compute="_compute_marge",
                help="Marge calculée sur base du prix de vente")
    description_fabricant = fields.Text('Description du fabricant', translate=True)
    date_tarif = fields.Date(string="Date du tarif")

    # Retrait de la catégorie par défaut (avec possibilité d'héritage)
    categ_id = fields.Many2one(default=lambda self: self._get_default_category_id())
    # Retrait de la société par défaut
    company_id = fields.Many2one(default=False)

    # Ajout de la catégorie d'udm pour permettre de filtrer les udms d'achat autorisées
    of_uom_category_id = fields.Many2one(related='uom_id.category_id')
    uom_po_id = fields.Many2one(domain="[('category_id', '=', of_uom_category_id)]")
    # Ajout de champs copiés de l'udm de vente pour affichage
    of_uom_po_id_display = fields.Many2one(related='uom_po_id', readonly=True)
    of_uom_po_id_display2 = fields.Many2one(related='uom_po_id', readonly=True)

    # Champs ajoutés pour openImport et affichage dans formulaire produit
    of_seller_pp_ht = fields.Float(related="seller_ids.pp_ht")
    of_seller_price = fields.Float(related="seller_ids.price", string="Prix d'achat")
    of_seller_remise = fields.Float(related="seller_ids.remise")
    of_seller_product_code = fields.Char(related="seller_ids.product_code")
    of_seller_product_category_name = fields.Char(related="seller_ids.of_product_category_name")

    @api.multi
    @api.depends('lst_price', 'standard_price')
    def _compute_marge(self):
        # la marge est calculée en fonction du prix de vente, faire en fonction du prix d'achat?
        for product in self:
            lst_price = product.lst_price
            if lst_price != 0:
                product.marge = (lst_price - product.standard_price) * 100.00 / lst_price
            else:  # division par 0!
                product.marge = -100

    def _get_default_category_id(self):
        return False

    @api.onchange('of_seller_pp_ht')
    def onchange_of_seller_pp_ht(self):
        if self.seller_ids:
            self.seller_ids[0].pp_ht = self.of_seller_pp_ht

    @api.onchange('of_seller_price')
    def onchange_of_seller_price(self):
        if self.seller_ids:
            self.seller_ids[0].price = self.of_seller_price

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _add_missing_default_values(self, values):
        # Mettre la référence produit (default_code) du template par défaut lors de la création d'une variante.
        if 'product_tmpl_id' in values and values['product_tmpl_id']:
            values['default_code'] = self.env['product.template'].browse(values['product_tmpl_id']).default_code
        return super(ProductProduct, self)._add_missing_default_values(values)

class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    # Champ inutile? Voir avec Aymeric
    # Probablement ajouté par erreur à la place de la fonctionnalité d'import avec ancienne-nouvelle références
    old_code = fields.Char(string="Ancienne Référence")
    pp_ht = fields.Float(string='Prix public HT', default=1.0, digits=dp.get_precision('Product Price'),
        required=True, help="Prix Public HT conseillé par le fabricant")
    pp_currency_id = fields.Many2one(related='currency_id')
    remise = fields.Float(string='Remise', digits=(4, 2), compute="_compute_remise")
    of_product_category_name = fields.Char("Catégorie fournisseur")

    # Retrait de la société par défaut
    company_id = fields.Many2one(default=False)

    @api.multi
    @api.depends('pp_ht', 'price')
    def _compute_remise(self):
        for supinfo in self:
            pp_ht = supinfo.pp_ht
            if pp_ht != 0:
                supinfo.remise = (pp_ht - supinfo.price) * 100.00 / pp_ht
            else:  # division par 0!
                supinfo.remise = -100
