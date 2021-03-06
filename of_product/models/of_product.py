# -*- coding: utf-8 -*-

from odoo import api, models, fields
import odoo.addons.decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = "product.template"

    modele = fields.Char(string='Modèle')
    marge = fields.Float(
        string='Marge', digits=(4, 2), compute="_compute_marge",
        help="Marge calculée sur base du prix de vente")
    description_fabricant = fields.Text('Description du fabricant', translate=True)
    date_tarif = fields.Date(string="Date du tarif")

    # Retrait de la catégorie par défaut (avec possibilité d'héritage)
    categ_id = fields.Many2one(default=lambda self: self._get_default_category_id())
    # Retrait de la société par défaut
    company_id = fields.Many2one(default=False)

    # Ajout de la catégorie d'udm pour permettre de filtrer les udms d'achat autorisées
    of_uom_category_id = fields.Many2one(related='uom_id.category_id', readonly=True)
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
    of_seller_delay = fields.Integer(related="seller_ids.delay")

    of_tag_ids = fields.Many2many(
        'of.product.template.tag', column1='product_id', column2='tag_id', string=u'Étiquettes')

    of_forbidden_discount = fields.Boolean(string=u"Remise interdite")

    # Structure de prix
    of_purchase_transport = fields.Float(string=u"Transport sur achat")
    of_sale_transport = fields.Float(string=u"Transport sur vente")
    of_sale_coeff = fields.Float(string=u"Coefficient de vente")
    of_other_logistic_costs = fields.Float(string=u"Autres frais logistiques")
    of_misc_taxes = fields.Float(string=u"Taxes divers")
    of_misc_costs = fields.Float(string=u"Frais divers")

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

    @api.multi
    def of_propage_cout(self, cout):
        # Le coût (standard_price) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env['res.company'].search(['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        property_obj = self.env['ir.property'].sudo()
        values = {product.id: cout for product in self}
        for company in companies:
            property_obj.with_context(force_company=company.id).set_multi('standard_price', 'product.product', values)

    @api.model
    def create(self, vals):
        propage_cout = 'standard_price' in vals
        if propage_cout:
            cout = vals.pop('standard_price')
        product = super(ProductProduct, self).create(vals)
        if propage_cout:
            product.of_propage_cout(cout)
        return product

    @api.multi
    def write(self, vals):
        propage_cout = 'standard_price' in vals
        if propage_cout:
            cout = vals.pop('standard_price')
        super(ProductProduct, self).write(vals)
        if propage_cout:
            self.of_propage_cout(cout)
        return True


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    # Champ inutile? Voir avec Aymeric
    # Probablement ajouté par erreur à la place de la fonctionnalité d'import avec ancienne-nouvelle références
    old_code = fields.Char(string="Ancienne Référence")
    pp_ht = fields.Float(
        string='Prix public HT', default=1.0, digits=dp.get_precision('Product Price'),
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


class ProductTemplateTag(models.Model):
    _name = "of.product.template.tag"

    name = fields.Char(string=u'Nom affiché', required=True, translate=True)
    description = fields.Text(string="Description")
    color = fields.Integer(string='Index Couleur')
    active = fields.Boolean(default=True)
    product_ids = fields.Many2many('product.template', column1='tag_id', column2='product_id', string='Produits')


class ProductCategory(models.Model):
    _inherit = "product.category"

    route_ids = fields.Many2many(
            'stock.location.route', 'stock_location_route_categ', 'categ_id', 'route_id', 'Routes',
            domain=[('product_categ_selectable', '=', True)], copy=True)
    of_layout_id = fields.Many2one('sale.layout_category', string="Section")

    @api.multi
    def copy_data(self, default=None):
        if default is None:
            default = {}
        default['name'] = self.name + u" (Copie)"
        default['property_account_creditor_price_difference_categ'] = \
            self.property_account_creditor_price_difference_categ
        default['property_account_income_categ_id'] = self.property_account_income_categ_id
        default['property_account_expense_categ_id'] = self.property_account_expense_categ_id
        default['property_stock_account_input_categ_id'] = self.property_stock_account_input_categ_id
        default['property_stock_account_output_categ_id'] = self.property_stock_account_output_categ_id
        default['property_stock_valuation_account_id'] = self.property_stock_valuation_account_id
        default['property_stock_journal'] = self.property_stock_journal
        res = super(ProductCategory, self).copy_data(default)
        return res
