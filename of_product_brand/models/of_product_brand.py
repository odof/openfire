# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OfProductBrand(models.Model):
    _name = 'of.product.brand'
    _order = 'name'

    name = fields.Char(string=u'Name', required=True)
    code = fields.Char(string=u'Code', required=True, oldname='prefix')
    use_prefix = fields.Boolean(
        string=u"Use code as prefix", default=True,
        help=u"The products internal references will be prefixed with the brand code")
    partner_id = fields.Many2one('res.partner', string=u'Supplier', domain=[('supplier', '=', True)], required=True)
    supplier_delay = fields.Integer(
        string=u'Delivery Delay (days)',
        help=u"The number of days it takes for the supplier to deliver products of this brand")
    product_ids = fields.One2many('product.template', 'brand_id', string=u'Products', readonly=True)
    product_variant_ids = fields.One2many('product.product', 'brand_id', string=u'Product variants', readonly=True)
    active = fields.Boolean(string=u'Active', default=True)
    logo = fields.Binary(string=u'Logo')
    product_count = fields.Integer(
        u'# Products', compute='_compute_product_count',
        help=u"The number of products of this brand")
    prices_date = fields.Date(
        compute='_compute_prices_date', store=True,
        help=u"Last price date of this brand's products.")
    note = fields.Text(string=u'Notes')
    product_change_warn = fields.Boolean(compute="_compute_product_change_warn")
    show_in_sales = fields.Boolean(
        string=u"Afficher dans les lignes de ventes",
        help=u"Si cette option est cochée, la marque sera ajoutée au début "
             u"du descriptif des lignes de commandes et factures")

    # les 2 champs suivant sont affichés dans le module of_import car il redéfini la vue form des marques
    description_sale = fields.Text(string=u"Description pour les devis")
    use_brand_description_sale = fields.Boolean(string=u"Utiliser la description vente au niveau de la marque")

    def _compute_product_count(self):
        read_group_res = self.env['product.template'].read_group(
            [('brand_id', 'in', self.ids)], ['brand_id'], ['brand_id'])
        group_data = dict((data['brand_id'][0], data['brand_id_count']) for data in read_group_res)
        for categ in self:
            categ.product_count = group_data.get(categ.id, 0)

    @api.depends('product_ids.date_tarif')
    def _compute_prices_date(self):
        product_obj = self.env['product.template']
        for brand in self:
            product = product_obj.search(
                [('brand_id', '=', brand.id), ('date_tarif', '!=', False)], order='date_tarif desc', limit=1)
            brand.prices_date = product.date_tarif

    @api.depends('code', 'use_prefix')
    def _compute_product_change_warn(self):
        brand_orig = getattr(self, '_origin', False)
        for brand in self:
            warn = False
            if brand_orig and brand_orig.product_ids:
                if brand.use_prefix != brand_orig.use_prefix:
                    warn = True
                elif brand.use_prefix and brand.code != brand_orig.code:
                    warn = True
            brand.product_change_warn = warn

    _sql_constraints = [
        ('code', 'unique(code)', "Another brand already exists with this code"),
    ]

    @api.model
    def create(self, vals):
        res = super(OfProductBrand, self).create(vals)
        if res.use_prefix:
            product_obj = self.env['product.product'].with_context(active_test=False)
            products = product_obj.search([('default_code', '=like', vals['code'] + r'\_%')])
            products.write({'brand_id': res.id})
        return res

    @api.multi
    def write(self, vals):
        previous_codes_dict = {brand.id: brand.code for brand in self}
        res = super(OfProductBrand, self).write(vals)
        for rec in self:
            if 'use_prefix' in vals or (rec.use_prefix and 'code' in vals):
                rec.update_products_default_code(remove_previous_prefix=previous_codes_dict[rec.id])
        return res

    @api.multi
    def update_products_default_code(self, products=False, remove_previous_prefix=False):
        """ Update products default_code according to brand values.
        @var self: Unique brand or empty browse record
        @var products: if not False, restrict update to these products
        @type products: browse records of product.product or of product.template or False
        @var remove_previous_prefix: remove previously exiting prefix. Can be set to True or to a specific string prefix
        @type remove_previous_prefix: boolean or string
        """
        if self:
            self.ensure_one()
            if products is False:
                products = self.with_context(active_test=False).product_variant_ids
            product_prefix = self.code + "_"
        if remove_previous_prefix and isinstance(remove_previous_prefix, basestring) and \
                not remove_previous_prefix.endswith('_'):
            remove_previous_prefix += '_'

        if not self.env.in_onchange:
            products = products.with_context(skip_default_code_lock=True)

        for product in products:
            # update_products_default_code() can be called from onchange, when default_code is not already filled
            default_code = product.default_code or ''
            if remove_previous_prefix:
                if isinstance(remove_previous_prefix, basestring):
                    if default_code.startswith(remove_previous_prefix):
                        default_code = default_code[len(remove_previous_prefix):]
                else:
                    # This part is dangerous as it may erase a part of the product default_code
                    ind = default_code.find("_")
                    default_code = default_code[ind + 1:]
            if self and default_code.startswith(product_prefix) != self.use_prefix:
                if self.use_prefix:
                    default_code = product_prefix + default_code
                else:
                    # @todo: is this part usefull?
                    default_code = product.default_code[len(product_prefix):]
            if product.default_code != default_code:
                product.default_code = default_code


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one(
        'of.product.brand', string='Brand', required=True, index=True,
        default=lambda s: s._default_brand_id())
    of_seller_name = fields.Many2one(related="seller_ids.name")
    of_previous_brand_id = fields.Many2one('of.product.brand', compute='_compute_of_previous_brand_id')
    seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id', 'Vendors', copy=True)

    @api.model
    def _default_brand_id(self):
        return self.env.ref('of_product_brand.main_brand', raise_if_not_found=False)

    # dependancy on default_code to prevent recomputing it before _onchange_brand_id call
    @api.depends('default_code')
    def _compute_of_previous_brand_id(self):
        for product in self:
            product.of_previous_brand_id = product.brand_id

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        # Mise à jour du préfixe de la marque sur l'article
        self.brand_id.update_products_default_code(products=self, remove_previous_prefix=self.of_previous_brand_id.code)

        # Création de la relation fournisseur
        if self.brand_id and not self.seller_ids:
            seller_data = {
                'name': self.brand_id.partner_id.id,
            }
            seller_data = self.env['product.supplierinfo']._add_missing_default_values(seller_data)
            self.seller_ids = [(0, 0, seller_data)]
        elif self.brand_id and len(self.seller_ids) == 1:
            self.seller_ids.name = self.brand_id.partner_id

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if self.default_code:
            ind = self.default_code.find('_')
            code = self.default_code[:ind]
            brand = self.env['of.product.brand'].search([('code', '=', code)])
            if brand:
                if brand != self.brand_id:
                    self.brand_id = brand
            else:
                if self.brand_id.use_prefix:
                    self.brand_id = False

    @api.model
    def of_name_search_extract_brands(self, name):
        brand_obj = self.env['of.product.brand']
        brands = brand_obj.browse()
        elems = []
        for elem in name.split(" "):
            if elem.startswith('m:') or elem.startswith('M:'):
                code = elem[2:]
                if not code:
                    continue
                b = brand_obj.search([('code', '=ilike', code)])
                if not b:
                    b = brand_obj.search([('name', '=ilike', code)])
                    if not b:
                        b = brand_obj.search([('name', '=ilike', code + '%')])
                if b:
                    brands += b
            else:
                elems.append(elem)
        name = " ".join(elems)
        return name, brands

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, brands = self.of_name_search_extract_brands(name)
        if brands:
            args = [('brand_id', 'in', brands._ids)] + args
        return super(ProductTemplate, self).name_search(name, args, operator, limit)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if 'default_code' not in default:
            default['default_code'] = _("%s (copy)") % self.default_code
        return super(ProductTemplate, self).copy(default=default)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    of_previous_brand_id = fields.Many2one('of.product.brand', compute='_compute_of_previous_brand_id')

    @api.depends('default_code')
    def _compute_of_previous_brand_id(self):
        for product in self:
            product.of_previous_brand_id = product.brand_id

    @api.constrains('default_code', 'brand_id', 'product_tmpl_id')
    def check_used_default_code(self):
        for product in self:
            if not product.default_code:
                continue
            if self.with_context(active_test=False).search([
                ('default_code', '=', product.default_code),
                ('brand_id', '=', product.brand_id.id),
                ('product_tmpl_id', '!=', product.product_tmpl_id.id)
            ], limit=1):
                raise ValidationError(
                    _('Product reference must be unique per brand !\nReference : %s') % product.default_code)

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        # Mise à jour du préfixe de la marque sur l'article
        self.brand_id.update_products_default_code(products=self, remove_previous_prefix=self.of_previous_brand_id.code)

        # Création de la relation fournisseur
        if self.brand_id and not self.seller_ids:
            seller_data = {
                'name': self.brand_id.partner_id.id,
            }
            seller_data = self.env['product.supplierinfo']._add_missing_default_values(seller_data)
            self.seller_ids = [(0, 0, seller_data)]
        elif self.brand_id and len(self.seller_ids) == 1:
            self.seller_ids.name = self.brand_id.partner_id

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if self.default_code:
            ind = self.default_code.find('_')
            code = self.default_code[:ind]
            brand = self.env['of.product.brand'].search([('code', '=', code)])
            if brand:
                if brand != self.brand_id:
                    self.brand_id = brand
            else:
                if self.brand_id.use_prefix:
                    self.brand_id = False

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, brands = self.env['product.template'].of_name_search_extract_brands(name)
        if brands:
            args = [('brand_id', 'in', brands._ids)] + args
        return super(ProductProduct, self).name_search(name, args, operator, limit)


class Partner(models.Model):
    _inherit = 'res.partner'

    brand_ids = fields.One2many('of.product.brand', 'partner_id', string="Brands", readonly=True)
    supplier_brand_count = fields.Integer(compute='_compute_supplier_brand_count', string='# Brands')

    @api.multi
    @api.depends('brand_ids')
    def _compute_supplier_brand_count(self):
        for partner in self:
            partner.supplier_brand_count = len(partner.brand_ids)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_product_brand_id = fields.Many2one(
        'of.product.brand', related='product_id.brand_id', string='Marque',
        store=True, index=True, readonly=True
    )

    @api.onchange('product_id')
    def product_id_change(self):
        result = super(SaleOrderLine, self).product_id_change()
        name = self.name
        if self.product_id.brand_id.use_brand_description_sale:
            # Recalcul du libellé de la ligne
            name = self.product_id.name_get()[0][1]
            brand_desc = self.env['mail.template'].with_context(safe=True).render_template(
                self.product_id.brand_id.description_sale, 'product.product', self.product_id.id, post_process=False)
            name += u'\n%s' % brand_desc
        if self.product_id.brand_id.show_in_sales:
            # Ajout de la marque dans le descriptif de l'article
            brand_code = self.product_id.brand_id.name + ' - '
            if name[0] == '[':
                i = name.find(']') + 1
                if name[i] == ' ':
                    i += 1
                name = name[:i] + brand_code + name[i:]
            else:
                name = brand_code + name
        self.name = name
        return result

    def _write(self, vals):
        for field in vals:
            if field != 'of_product_brand_id':
                break
        else:
            self = self.sudo()
        return super(SaleOrderLine, self)._write(vals)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    of_product_brand_id = fields.Many2one(
        'of.product.brand', related='product_id.brand_id', string='Marque',
        store=True, index=True, readonly=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        super(AccountInvoiceLine, self)._onchange_product_id()
        name = self.name
        if self.product_id.brand_id.use_brand_description_sale:
            # Recalcul du libelllé de la ligne
            name = self.product_id.name_get()[0][1]
            brand_desc = self.env['mail.template'].render_template(
                self.product_id.brand_id.description_sale, 'product.product', self.product_id.id, post_process=False)
            name += u'\n%s' % brand_desc
        if self.product_id.brand_id.show_in_sales:
            # Ajout de la marque dans le descriptif de l'article
            brand_code = self.product_id.brand_id.name + ' - '
            if name[0] == '[':
                i = name.find(']') + 1
                if name[i] == ' ':
                    i += 1
                name = name[:i] + brand_code + name[i:]
            else:
                name = brand_code + name
        self.name = name

    def _write(self, vals):
        for field in vals:
            if field != 'of_product_brand_id':
                break
        else:
            self = self.sudo()
        return super(AccountInvoiceLine, self)._write(vals)


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_restricted_brand_ids = fields.Many2many(
        comodel_name='of.product.brand', column1='user_id', column2='brand_id',
        relation='of_product_brand_res_users_rel2',
        string=u"Marques non autorisées",
        help=u"Marques non visibles par l'utilisateur")
    of_readonly_brand_ids = fields.Many2many(
        comodel_name='of.product.brand', column1='res_users_id', column2='of_product_brand_id',
        relation='of_product_brand_res_users_rel',
        string=u"Marques non modifiables",
        help=u"Marques de produits non autorisées pour les utilisateurs assignés")
