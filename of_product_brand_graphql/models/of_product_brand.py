# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class OFProductBrand(models.Model):
    _inherit = 'of.product.brand'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if 'active' in args.keys():
            mutation['active'] = args['active']

        if code := args.get('code'):
            mutation['code'] = code

        if 'use_prefix' in args.keys():
            mutation['use_prefix'] = args['use_prefix']

        if supplier_delay := args.get('supplier_delay'):
            mutation['supplier_delay'] = supplier_delay

        if product_templates := args.get('product_templates'):
            mutation['product_ids'] = x2many(self=self, model='product.template', input=product_templates)

        if products := args.get('products'):
            mutation['product_variant_ids'] = x2many(self=self, model='product.product', input=products)

        return mutation
