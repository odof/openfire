# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.addons.of_utils.models.of_utils import is_valid_url


class ProductCategory(models.Model):
    _inherit = "product.category"

    route_ids = fields.Many2many(
            'stock.location.route', 'stock_location_route_categ', 'categ_id', 'route_id', 'Routes',
            domain=[('product_categ_selectable', '=', True)], copy=True)
    of_layout_id = fields.Many2one('sale.layout_category', string="Section")
    # Uniformisation de la méthode de coût sur les sociétés (effectif si of_base_multicompany est installé)
    property_cost_method = fields.Selection(of_unify_companies=True)
    of_stock_update_standard_price = fields.Boolean(
        string=u"Mettre à jour le coût des articles suite aux mouvements de stock", default=True)
    of_import_update_standard_price = fields.Boolean(string=u"Mettre à jour le coût des articles suite aux imports")
    of_sale_cost = fields.Selection(
        selection=[('theoretical', u"Coût théorique"), ('standard', u"Coût standard")], string=u"Coût pour les ventes",
        help=u"Le coût choisi sera repris dans les commandes et factures de vente.", required=True,
        default='theoretical')

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
    # Uniformisation de la méthode de coût sur les sociétés (effectif si of_base_multicompany est installé)
    # Normalement inutile car la modification de cette valeur est inhibée par Odoo (cf commit af9d21b3) pour préférer
    # une gestion directement depuis les catégories d'articles
    property_cost_method = fields.Selection(of_unify_companies=True)

    # Ajout de la catégorie d'udm pour permettre de filtrer les udms d'achat autorisées
    of_uom_category_id = fields.Many2one(related='uom_id.category_id', readonly=True)
    uom_po_id = fields.Many2one(domain="[('category_id', '=', of_uom_category_id)]")
    # Ajout de champs copiés de l'udm de vente pour affichage
    of_uom_po_id_display = fields.Many2one(related='uom_po_id', readonly=True)
    of_uom_po_id_display2 = fields.Many2one(related='uom_po_id', readonly=True)

    # Champs ajoutés pour openImport et affichage dans formulaire produit
    of_seller_pp_ht = fields.Float(related="seller_ids.pp_ht", related_sudo=False)
    of_seller_price = fields.Float(related="seller_ids.price", string="Prix d'achat", related_sudo=False)
    of_seller_remise = fields.Float(related="seller_ids.remise", related_sudo=False)
    of_seller_product_code = fields.Char(related="seller_ids.product_code", related_sudo=False)
    of_seller_product_name = fields.Char(related="seller_ids.product_name", related_sudo=False)
    of_seller_product_category_name = fields.Char(related="seller_ids.of_product_category_name", related_sudo=False)
    of_seller_delay = fields.Integer(related="seller_ids.delay")

    of_tag_ids = fields.Many2many(
        'of.product.template.tag', column1='product_id', column2='tag_id', string=u'Étiquettes')
    of_linked_product_ids = fields.Many2many(
        comodel_name='product.template', column1='of_product_template1_id', column2='of_product_template2_id',
        relation='linked_product_rel', string=u"Articles liés")

    of_forbidden_discount = fields.Boolean(string=u"Remise interdite")

    of_obsolete = fields.Boolean(string=u"Article obsolète")

    # Structure de prix
    of_purchase_transport = fields.Float(string=u"Transport sur achat")
    of_sale_transport = fields.Float(string=u"Transport sur vente")
    of_sale_coeff = fields.Float(string=u"Coefficient de vente")
    of_other_logistic_costs = fields.Float(string=u"Autres frais logistiques")
    of_misc_taxes = fields.Float(string=u"Taxes divers")
    of_misc_costs = fields.Float(string=u"Frais divers")
    of_url = fields.Char(string=u"URL")

    # Gestion du coût standard et du coût théorique
    standard_price = fields.Float(
        help=u"Le coût est exprimé dans l'unité de mesure par défaut de l'article.\n"
             u"Correspond au coût calculé selon la \"méthode de coût\" définie dans la catégorie de l'article. "
             u"Cette valeur de coût est celle utilisée pour la valorisation de l'inventaire.")
    of_theoretical_cost = fields.Float(
        string=u"Coût théorique", compute='_compute_of_theoretical_cost',
        inverse='_set_of_theoretical_cost', search='_search_of_theoretical_cost',
        digits=dp.get_precision('Product Price'), groups="base.group_user",
        help=u"Correspond au coût calculé par application des règles définies dans la marque ou dans les fichiers "
             u"d'import. Cette valeur de coût peut servir pour le calcul de la marge dans les devis et les factures ; "
             u"elle n'est en revanche jamais utilisée pour la valorisation de l'inventaire.")

    @api.depends('product_variant_ids', 'product_variant_ids.of_theoretical_cost')
    def _compute_of_theoretical_cost(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.of_theoretical_cost = template.product_variant_ids.of_theoretical_cost
        for template in (self - unique_variants):
            template.of_theoretical_cost = 0.0

    @api.one
    def _set_of_theoretical_cost(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.of_theoretical_cost = self.of_theoretical_cost
            # On répercute le changement sur le coût standard
            if self.cost_method not in ('average', 'real'):
                self.product_variant_ids.standard_price = self.of_theoretical_cost

    def _search_of_theoretical_cost(self, operator, value):
        products = self.env['product.product'].search([('of_theoretical_cost', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]

    @api.one
    def _set_standard_price(self):
        super(ProductTemplate, self)._set_standard_price()
        # On répercute le changement sur le coût théorique
        if len(self.product_variant_ids) == 1 and self.cost_method not in ('average', 'real'):
            self.product_variant_ids.of_theoretical_cost = self.standard_price

    @api.multi
    def get_cost(self):
        self.ensure_one()
        if self.cost_method not in ('average', 'real') or self.categ_id.of_sale_cost == 'standard':
            return self.standard_price
        else:
            return self.of_theoretical_cost

    @api.multi
    @api.depends('lst_price', 'standard_price', 'of_theoretical_cost')
    def _compute_marge(self):
        # la marge est calculée en fonction du prix de vente, faire en fonction du prix d'achat?
        for product in self:
            lst_price = product.lst_price
            if lst_price != 0:
                product.marge = (lst_price - product.get_cost()) * 100.00 / lst_price
            else:  # division par 0!
                product.marge = 0

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

    def _get_related_fields_variant_template(self):
        related_fields = super(ProductTemplate, self)._get_related_fields_variant_template()
        related_fields.append('of_theoretical_cost')
        return related_fields

    @api.model
    def create(self, vals):
        if vals.get('of_url') and not is_valid_url(vals['of_url']):
            raise UserError(u"L'URL saisie n'est pas correcte !")

        if not vals.get('categ_id'):
            # Récupération de la catégorie par défaut, basée sur la fonction _get_default_category_id du module product
            # Ceci afin d'éviter des erreurs à l'installation de modules qui veulent créer des articles sans préciser
            # leur catégorie
            categ_id = self._context.get('categ_id') or self._context.get('default_categ_id')
            if not categ_id:
                category = self.env.ref('product.product_category_all', raise_if_not_found=False)
                categ_id = category and category.type == 'normal' and category.id
            if categ_id:
                vals['categ_id'] = categ_id

        # On désactive le log dans le RSE pour gagner du temps lors d'import d'articles
        return super(ProductTemplate, self.with_context(mail_create_nolog=True)).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('of_url') and not is_valid_url(vals['of_url']):
            raise UserError(u"L'URL saisie n'est pas correcte !")

        return super(ProductTemplate, self).write(vals)


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price = fields.Float(
        of_unify_companies=True,
        help=u"Le coût est exprimé dans l'unité de mesure par défaut de l'article.\n"
             u"Correspond au coût calculé selon la \"méthode de coût\" définie dans la catégorie de l'article. "
             u"Cette valeur de coût est celle utilisée pour la valorisation de l'inventaire.")
    of_theoretical_cost = fields.Float(
        string=u"Coût théorique", digits=dp.get_precision('Product Price'), groups="base.group_user",
        help=u"Correspond au coût calculé par application des règles définies dans la marque ou dans les fichiers "
             u"d'import. Cette valeur de coût peut servir pour le calcul de la marge dans les devis et les factures ; "
             u"elle n'est en revanche jamais utilisée pour la valorisation de l'inventaire.")

    @api.model
    def _add_missing_default_values(self, values):
        # Mettre la référence produit (default_code) du template par défaut lors de la création d'une variante.
        if 'product_tmpl_id' in values and values['product_tmpl_id']:
            values['default_code'] = self.env['product.template'].browse(values['product_tmpl_id']).default_code
        return super(ProductProduct, self)._add_missing_default_values(values)

    @api.multi
    def _set_standard_price(self, value):
        # Le coût (standard_price) est défini sur l'ensemble des sociétés.
        # Il en va donc de même pour l'historique des prix
        companies = self.env['res.company'].search(['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        for company in companies:
            super(ProductProduct, self.with_context(force_company=company.id))._set_standard_price(value)

    @api.multi
    def get_cost(self):
        if not self:
            return 0
        self.ensure_one()
        if self.cost_method not in ('average', 'real') or self.categ_id.of_sale_cost == 'standard':
            return self.standard_price
        else:
            return self.of_theoretical_cost

    @api.model
    def create(self, vals):
        product = super(ProductProduct, self).create(vals)
        if product.cost_method not in ('average', 'real'):
            product.of_theoretical_cost = product.standard_price

        product.of_purchase_coeff_cost_propagation(product.get_cost())

        return product

    @api.multi
    def write(self, values):
        res = super(ProductProduct, self).write(values)

        for product in self:
            if product.cost_method not in ('average', 'real'):
                if 'standard_price' in values and values['standard_price'] != product.of_theoretical_cost:
                    product.of_theoretical_cost = product.standard_price
                elif 'of_theoretical_cost' in values and values['of_theoretical_cost'] != product.standard_price:
                    product.standard_price = product.of_theoretical_cost

            if (product.cost_method not in ('average', 'real') or product.categ_id.of_sale_cost == 'standard') and \
                    'standard_price' in values:
                product.of_purchase_coeff_cost_propagation(product.standard_price)
            elif product.cost_method in ('average', 'real') and product.categ_id.of_sale_cost == 'theoretical' and \
                    'of_theoretical_cost' in values:
                product.of_purchase_coeff_cost_propagation(product.of_theoretical_cost)

        return res


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

    # On retire ces champs de ceux repris par la duplication
    product_name = fields.Char(copy=False)
    product_code = fields.Char(copy=False)

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
