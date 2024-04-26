# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if list_price := args.get('list_price'):
            mutation['list_price'] = list_price

        if category := args.get('category'):
            mutation['categ_id'] = many2one(self=self, model='product.category', input=category)

        return mutation
