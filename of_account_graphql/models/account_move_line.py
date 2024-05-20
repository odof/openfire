# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _prepare_mutation_values(self, input, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if quantity := args.get('quantity'):
            mutation['quantity'] = quantity

        if price_unit := args.get('price_unit'):
            mutation['price_unit'] = price_unit

        if product := args.get('product'):
            mutation['product_id'] = many2one(self=self, model='product.product', input=product)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='account.move.line', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'ilike', select.name)]

        return odoo_domain
