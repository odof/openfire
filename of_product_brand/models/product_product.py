# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


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
                raise ValidationError(
                    _("Product reference must be unique per brand !\nReference : %s") % product.default_code)

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

    @api.depends('default_code')
    def _compute_brand_id(self):
        for product in self:
            if product.default_code:
                ind = product.default_code.find('_')
                code = product.default_code[:ind]
                brand = self.env['of.product.brand'].search([('code', '=', code)], limit=1)
                if brand:
                    if brand != product.brand_id:
                        product.brand_id = brand
                elif product.brand_id.use_prefix:
                    # Empty the brand if the product code doesn't match the current brand code
                    product.brand_id = False

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        name, brands = self.env['product.template'].of_name_search_extract_brands(name)
        if brands:
            args = [['brand_id', 'in', brands._ids]] + args
        return super()._name_search(name, args, operator, limit, name_get_uid)
