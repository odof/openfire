# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


class OFPlanningInterventionLine(models.Model):
    _inherit = 'of.planning.intervention.line'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if price_unit := args.get('price_unit'):
            mutation['price_unit'] = price_unit

        if name := args.get('name'):
            mutation['name'] = name

        if discount := args.get('discount'):
            mutation['discount'] = discount

        if quantity := args.get('quantity'):
            mutation['qty'] = quantity

        if product := args.get('product'):
            mutation['product_id'] = many2one(self=self, model='product.product', input=product)

        if 'taxes' in args:
            mutation['tax_ids'] = x2many(self=self, model='account.tax', input=args.get('taxes'))

        return mutation
