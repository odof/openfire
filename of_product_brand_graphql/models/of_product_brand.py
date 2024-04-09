# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFProductBrand(models.Model):
    _inherit = 'of.product.brand'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if 'active' in args:
            mutation['active'] = args['active']

        if code := args.get('code'):
            mutation['code'] = code

        if 'use_prefix' in args:
            mutation['use_prefix'] = args['use_prefix']

        if supplier_delay := args.get('supplier_delay'):
            mutation['supplier_delay'] = supplier_delay

        if 'product_templates' in args:
            mutation['product_ids'] = x2many(self=self, model='product.template', input=args.get('product_templates'))

        if 'products' in args:
            mutation['product_variant_ids'] = x2many(self=self, model='product.product', input=args.get('products'))

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.product.brand', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
