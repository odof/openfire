# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class OfProductBrand(models.Model):
    _name = 'of.product.brand'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, oldname='prefix')
    use_prefix = fields.Boolean(string="Use code as prefix", default=True, help="The products internal references will be prefixed with the brand code")
    partner_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier', '=', True)], required=True)
    product_ids = fields.One2many('product.template', 'brand_id', string='Products', readonly=True)
    product_variant_ids = fields.One2many('product.product', 'brand_id', string='Product variants', readonly=True)
    active = fields.Boolean(string='Active', default=True)
    logo = fields.Binary(string='Logo')
    product_count = fields.Integer(
        '# Products', compute='_compute_product_count',
        help="The number of products of this brand")
    note = fields.Text(string='Notes')
    product_change_warn = fields.Boolean(compute="_compute_product_change_warn")
    show_in_sales = fields.Boolean(
        string="Afficher dans les lignes de ventes",
        help="Si cette option est cochée, la marque sera ajoutée au début du descriptif des lignes de commandes et factures")
    # les 2 champs suivant sont affichés dans le module of_import car il redéfini la vue form des marques
    description_sale = fields.Text(string=u"Description pour les devis")
    use_brand_description_sale = fields.Boolean(string=u"Utiliser la description vente au niveau de la marque")

    def _compute_product_count(self):
        read_group_res = self.env['product.template'].read_group([('brand_id', 'in', self.ids)], ['brand_id'], ['brand_id'])
        group_data = dict((data['brand_id'][0], data['brand_id_count']) for data in read_group_res)
        for categ in self:
            categ.product_count = group_data.get(categ.id, 0)

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
        previous_code = self and self.code
        super(OfProductBrand, self).write(vals)
        if 'use_prefix' in vals or (self.use_prefix and 'code' in vals):
            self.update_products_default_code(remove_previous_prefix=previous_code)
        return True

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
        if remove_previous_prefix and isinstance(remove_previous_prefix, basestring) and not remove_previous_prefix.endswith('_'):
            remove_previous_prefix += '_'
        for product in products:
            default_code = product.default_code or ''  # update_products_default_code() can be called from onchange, when default_code is not already filled
            if remove_previous_prefix:
                if isinstance(remove_previous_prefix, basestring):
                    if default_code.startswith(remove_previous_prefix):
                        default_code = default_code[len(remove_previous_prefix):]
                else:
                    # This part is dangerous as it may erase a part of the product default_code
                    ind = default_code.find("_")
                    default_code = default_code[ind+1:]
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

    brand_id = fields.Many2one('of.product.brand', string='Brand', required=True, index=True)
    of_seller_name = fields.Many2one(related="seller_ids.name")
    of_previous_brand_id = fields.Many2one('of.product.brand', compute='_compute_of_previous_brand_id')
    seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id', 'Vendors', copy=True)

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
                raise ValidationError(_('Product reference must be unique per brand !\nReference : %s') % product.default_code)

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
