# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfProductBrand(models.Model):
    _name = 'of.product.brand'
    _order = 'name'

    _description = "Product brand"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    use_prefix = fields.Boolean(
        string="Use code as prefix", default=True,
        help="The products internal references will be prefixed with the brand code")
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Supplier", domain=[('supplier_rank', '>', 0)], required=True)
    supplier_delay = fields.Integer(
        string="Delivery Delay (days)",
        help="The number of days it takes for the supplier to deliver products of this brand")
    product_ids = fields.One2many(
        comodel_name='product.template', inverse_name='brand_id', string="Products", readonly=True)
    product_variant_ids = fields.One2many(
        comodel_name='product.product', inverse_name='brand_id', string="Product variants", readonly=True)
    logo = fields.Binary(string="Logo")
    product_count = fields.Integer(
        string="# Products", compute='_compute_product_count', help="The number of products of this brand")
    price_date = fields.Date(
        compute='_compute_price_date', store=True, help="Last price date of this brand's products.")
    note = fields.Text(string="Notes")
    product_change_warn = fields.Boolean(compute='_compute_product_change_warn')
    show_in_sales = fields.Boolean(
        string="Show in sales order lines",
        help="If this option is checked, the brand will be added at the beginning of the description "
             "of order and invoice lines")
    description_sale = fields.Text(string="Description for quotations")
    use_brand_description_sale = fields.Boolean(string="Use brand-level sales description")

    def _compute_product_count(self):
        read_group_res = self.env['product.template'].read_group(
            [('brand_id', 'in', self.ids)], ['brand_id'], ['brand_id'])
        group_data = {
            data['brand_id'][0]: data['brand_id_count'] for data in read_group_res
        }
        for categ in self:
            categ.product_count = group_data.get(categ.id, 0)

    @api.depends('product_ids.of_cost_date')
    def _compute_price_date(self):
        product_obj = self.env['product.template']
        for brand in self:
            product = product_obj.search(
                [('brand_id', '=', brand.id), ('of_cost_date', '!=', False)], order='of_cost_date desc', limit=1)
            brand.price_date = product.of_cost_date if product else False

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

    @api.model_create_multi
    def create(self, vals_list):
        # TODO: Useless part since the brand is required on the product
        brands = super().create(vals_list)
        for vals in vals_list:
            for brand in brands.filtered(lambda b: b.use_prefix):
                product_obj = self.env['product.product'].with_context(active_test=False)
                products = product_obj.search([('default_code', '=like', vals['code'] + r'\_%')])
                products.write({'brand_id': brand.id})
        return brands

    def write(self, vals):
        previous_codes_dict = {brand.id: brand.code for brand in self}
        res = super().write(vals)
        for rec in self:
            if 'use_prefix' in vals or (rec.use_prefix and 'code' in vals):
                rec.update_products_default_code(remove_previous_prefix=previous_codes_dict[rec.id])
        return res

    def update_products_default_code(self, products=False, remove_previous_prefix=False):
        """Update products default_code according to brand values.

        :param self: Unique brand or empty browse record
        :param products: if not False, restrict update to these products
        :type products: browse records of product.product or of product.template or False
        :param remove_previous_prefix: remove previously exiting prefix. Can be set to True or to a specific
            string prefix
        :type remove_previous_prefix: boolean or string
        :return: None
        """
        if self:
            self.ensure_one()
            if products is False:
                products = self.with_context(active_test=False).product_variant_ids
            product_prefix = f"{self.code}_"
        if remove_previous_prefix and isinstance(remove_previous_prefix, str) \
                and not remove_previous_prefix.endswith('_'):
            remove_previous_prefix += '_'
        for product in products.with_context(skip_default_code_lock=True):
            # update_products_default_code() can be called from onchange, when default_code is not already filled
            default_code = product.default_code or ''
            if remove_previous_prefix:
                if isinstance(remove_previous_prefix, str):
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
