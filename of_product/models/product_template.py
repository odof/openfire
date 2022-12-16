# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.addons.of_utils.models.misc import is_valid_url


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_model = fields.Char(string="Model")
    of_margin = fields.Float(
        string="Margin", digits=(4, 2), compute='_compute_of_margin',
        help="Margin calculated on the basis of the sale price")
    of_manufacturer_description = fields.Text(string="Manufacturer Description", translate=True)
    of_cost_date = fields.Date(string="Cost date")

    # Retrait de la catégorie par défaut (avec possibilité d'héritage)
    categ_id = fields.Many2one(default=lambda self: self._get_default_category_id())
    # Retrait de la société par défaut
    company_id = fields.Many2one(default=False)
    # Uniformisation de la méthode de coût sur les sociétés (effectif si of_base_multicompany est installé)
    # Normalement inutile car la modification de cette valeur est inhibée par Odoo (cf commit af9d21b3) pour préférer
    # une gestion directement depuis les catégories d'articles
    cost_method = fields.Selection(of_unify_companies=True)

    # Ajout de la catégorie d'udm pour permettre de filtrer les udms d'achat autorisées
    of_uom_category_id = fields.Many2one(related='uom_id.category_id', readonly=True)
    uom_po_id = fields.Many2one(domain="[('category_id', '=', of_uom_category_id)]")
    # Ajout de champs copiés de l'udm de vente pour affichage
    of_uom_po_id_display = fields.Many2one(related='uom_po_id', readonly=True)
    of_uom_po_id_display2 = fields.Many2one(related='uom_po_id', readonly=True)

    # Champs ajoutés pour openImport et affichage dans formulaire produit
    of_seller_pp_untaxed = fields.Float(related='seller_ids.of_public_price_untaxed', related_sudo=False)
    of_seller_price = fields.Float(related='seller_ids.price', string="Purchase price", related_sudo=False)
    of_seller_discount = fields.Float(related='seller_ids.of_discount', related_sudo=False)
    of_seller_product_code = fields.Char(related='seller_ids.product_code', related_sudo=False)
    of_seller_product_name = fields.Char(related='seller_ids.product_name', related_sudo=False)
    of_seller_product_category_name = fields.Char(related='seller_ids.of_product_category_name', related_sudo=False)
    of_seller_delay = fields.Integer(related='seller_ids.delay')

    of_linked_product_ids = fields.Many2many(
        comodel_name='product.template', column1='of_product_template1_id', column2='of_product_template2_id',
        relation='linked_product_rel', string="Related products")

    of_forbidden_discount = fields.Boolean(string="Forbiden discount")

    of_obsolete = fields.Boolean(string="Obsolete item")

    # Structure de prix
    of_purchase_transport = fields.Float(string="Transport on purchase")
    of_sale_transport = fields.Float(string="Transport on sale")
    of_sale_coeff = fields.Float(string="Sale coefficient")
    of_other_logistic_costs = fields.Float(string="Other logistics costs")
    of_misc_taxes = fields.Float(string="Miscellaneous taxes")
    of_misc_costs = fields.Float(string="Miscellaneous costs")
    of_url = fields.Char(string="URL")

    # Gestion du coût standard et du coût théorique
    of_theoretical_cost = fields.Float(
        string="Theoretical cost", compute='_compute_of_theoretical_cost',
        inverse='_set_of_theoretical_cost', search='_search_of_theoretical_cost',
        digits='Product Price', groups='base.group_user',
        help="Corresponds to the cost calculated by applying the rules defined in the brand or in the import files. "
             "This cost value can be used for margin calculation in quotes and invoices; however, it is never used for "
             "inventory valuation.")

    @api.depends('product_variant_ids', 'product_variant_ids.of_theoretical_cost')
    def _compute_of_theoretical_cost(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.of_theoretical_cost = template.product_variant_ids.of_theoretical_cost
        for template in (self - unique_variants):
            template.of_theoretical_cost = 0.0

    def _set_of_theoretical_cost(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.of_theoretical_cost = template.of_theoretical_cost
                # On répercute le changement sur le coût standard
                if template.cost_method == 'standard':
                    template.product_variant_ids.standard_price = template.of_theoretical_cost

    def _search_of_theoretical_cost(self, operator, value):
        products = self.env['product.product'].search([('of_theoretical_cost', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]

    def _set_standard_price(self):
        super(ProductTemplate, self)._set_standard_price()
        # On répercute le changement sur le coût théorique
        for template in self:
            if len(template.product_variant_ids) == 1 and template.cost_method == 'standard':
                template.product_variant_ids.of_theoretical_cost = template.standard_price

    def get_cost(self):
        self.ensure_one()
        if self.cost_method == 'standard' or self.categ_id.of_sale_cost == 'standard':
            return self.standard_price
        else:
            return self.of_theoretical_cost

    @api.depends('list_price', 'standard_price', 'of_theoretical_cost')
    def _compute_of_margin(self):
        # la marge est calculée en fonction du prix de vente, faire en fonction du prix d'achat?
        for product in self:
            list_price = product.list_price
            if list_price != 0:
                product.of_margin = (list_price - product.get_cost()) * 100.00 / list_price
            else:  # division par 0!
                product.of_margin = -100

    def _get_default_category_id(self):
        return False

    @api.onchange('of_seller_pp_untaxed')
    def onchange_of_seller_pp_untaxed(self):
        if self.seller_ids:
            self.seller_ids[0].of_public_price_untaxed = self.of_seller_pp_untaxed

    @api.onchange('of_seller_price')
    def onchange_of_seller_price(self):
        if self.seller_ids:
            self.seller_ids[0].price = self.of_seller_price

    def _get_related_fields_variant_template(self):
        related_fields = super(ProductTemplate, self)._get_related_fields_variant_template()
        related_fields.append('of_theoretical_cost')
        return related_fields

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('of_url') and not is_valid_url(vals['of_url']):
                raise UserError(_("The entered URL is not correct !"))

            if not vals.get('categ_id'):
                # Récupération de la catégorie par défaut, basée sur la fonction _get_default_category_id du module
                # product. Ceci afin d'éviter des erreurs à l'installation de modules qui veulent créer des articles
                # sans préciser leur catégorie
                categ_id = self._context.get('categ_id') or self._context.get('default_categ_id')
                if not categ_id:
                    category = self.env.ref('product.product_category_all', raise_if_not_found=False)
                    categ_id = category and category.type == 'normal' and category.id
                if categ_id:
                    vals['categ_id'] = categ_id

        # On désactive le log dans le RSE pour gagner du temps lors d'import d'articles
        return super(ProductTemplate, self.with_context(mail_create_nolog=True)).create(vals_list)

    def write(self, vals):
        if vals.get('of_url') and not is_valid_url(vals['of_url']):
            raise UserError(_("The entered URL is not correct !"))
        return super(ProductTemplate, self).write(vals)
