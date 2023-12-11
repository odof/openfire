# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import Command, _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _default_brand_id(self):
        return self.env.ref('of_product_brand.main_brand', raise_if_not_found=False)

    brand_id = fields.Many2one(
        comodel_name='of.product.brand',
        string="Brand",
        compute='_compute_brand_id',
        store=True,
        readonly=False,
        required=True,
        index=True,
        default=lambda s: s._default_brand_id(),
    )
    of_seller_partner_id = fields.Many2one(related='seller_ids.partner_id')
    of_previous_brand_id = fields.Many2one(comodel_name='of.product.brand', compute='_compute_of_previous_brand_id')
    seller_ids = fields.One2many(
        comodel_name='product.supplierinfo', inverse_name='product_tmpl_id', string="Vendors", copy=True
    )

    # ---------------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------------

    # dependancy on default_code to prevent recomputing it before _onchange_brand_id call
    @api.depends('default_code')
    def _compute_of_previous_brand_id(self):
        for product in self:
            product.of_previous_brand_id = product.brand_id

    @api.depends('default_code')
    def _compute_brand_id(self):
        for product in self:
            if product.default_code:
                ind = product.default_code.find('_')
                code = product.default_code[:ind]
                if brand := self.env['of.product.brand'].search([('code', '=', code)], limit=1):
                    if brand != product.brand_id:
                        product.brand_id = brand
                elif product.brand_id.use_prefix:
                    # Empty the brand if the product code doesn't match the current brand code
                    product.brand_id = False

    # ---------------------------------------------------------------------
    # Onchange methods
    # ---------------------------------------------------------------------

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        # Mise à jour du préfixe de la marque sur l'article
        self.brand_id.update_products_default_code(products=self, remove_previous_prefix=self.of_previous_brand_id.code)

        # Création de la relation fournisseur
        if self.brand_id:
            if not self.seller_ids:
                seller_data = {
                    'partner_id': self.brand_id.partner_id.id,
                }
                seller_data = self.env['product.supplierinfo']._add_missing_default_values(seller_data)
                self.seller_ids = [Command.create(seller_data)]
            elif len(self.seller_ids) == 1:
                self.seller_ids.partner_id = self.brand_id.partner_id

    # ---------------------------------------------------------------------
    # ORM methods
    # ---------------------------------------------------------------------

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

    # ---------------------------------------------------------------------
    # Business methods
    # ---------------------------------------------------------------------

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

    def _recompute_product_name(self):
        """Recompute the product name based on the brand's description_sale and show_in_sales fields.
        :return: str Computed product name
        """
        self.ensure_one()
        product_name = self.name_get()[0][1]
        if self.description_sale:
            product_name += '\n' + self.description_sale
        if self.brand_id.use_brand_description_sale:
            # Recalcul du libellé de la ligne
            product_name = self.name_get()[0][1]
            # Only inline templates are supported here.
            # ie: {{ description_sale and '\n' + description_sale or '' }}
            brand_desc = (
                self.env['mail.template']
                .with_context(safe=True)
                ._render_template(
                    self.brand_id.description_sale,
                    self._name,
                    [self.id],
                    post_process=False,
                )[self.id]
            )
            product_name += '\n%s' % brand_desc
        if self.brand_id.show_in_sales:
            # Ajout de la marque dans le descriptif de l'article
            brand_code = f'{self.brand_id.name} - '
            # This regex will match the first occurrence of "[XXXX]" in the product's name as the default code
            # and will capture the rest of the string.
            # So if the product's name is "[XXXX] This is the product's [YYYY] name" it will capture groups
            # as : "[XXXX] " and "This is the product's [YYYY] name"
            regex = r"(^\[\S+\] )(.*)"
            if re.search(regex, product_name) is not None:
                # product's name is required so we should always have 2 groups here
                subst = f"\\g<1>{brand_code}\\g<2>"
                product_name = re.sub(regex, subst, product_name, 0, re.MULTILINE)
            else:
                product_name = brand_code + product_name
        return product_name
