# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if product_uom_qty := args.get('product_uom_qty'):
            mutation['product_uom_qty'] = product_uom_qty

        if price_unit := args.get('price_unit'):
            mutation['price_unit'] = price_unit

        if price_subtotal := args.get('price_subtotal'):
            mutation['price_subtotal'] = price_subtotal

        if 'taxes' in args:
            mutation['tax_id'] = x2many(self=self, model='account.tax', input=args.get('taxes'))

        if product := args.get('product'):
            mutation['product_id'] = many2one(self=self, model='product.product', input=product)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='sale.order.line', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
