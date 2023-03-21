# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one(
        comodel_name='of.product.brand', string="Brand", required=True, index=True,
        default=lambda s: s._default_brand_id())
    of_seller_partner_id = fields.Many2one(related='seller_ids.partner_id')
    of_previous_brand_id = fields.Many2one(comodel_name='of.product.brand', compute='_compute_of_previous_brand_id')
    seller_ids = fields.One2many(
        comodel_name='product.supplierinfo', inverse_name='product_tmpl_id', string="Vendors", copy=True)

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
                'partner_id': self.brand_id.partner_id.id,
            }
            seller_data = self.env['product.supplierinfo']._add_missing_default_values(seller_data)
            self.seller_ids = [(0, 0, seller_data)]

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if self.default_code:
            ind = self.default_code.find('_')
            code = self.default_code[:ind]
            brand = self.env['of.product.brand'].search([('code', '=', code)], limit=1)
            if brand:
                if brand != self.brand_id:
                    self.brand_id = brand
            elif self.brand_id.use_prefix:
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
                    b = brand_obj.search([('name', '=ilike', f'{code}%')])
                if b:
                    brands += b
            else:
                elems.append(elem)
        name = " ".join(elems)
        return name, brands

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        name, brands = self.of_name_search_extract_brands(name)
        if brands:
            args = [['brand_id', 'in', brands._ids]] + args
        return super()._name_search(name, args, operator, limit, name_get_uid)

    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if 'default_code' not in default and self.default_code:
            default['default_code'] = _("%s (copy)") % self.default_code
        return super().copy(default=default)
