# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if partner := args.get('partner'):
            mutation['partner_id'] = many2one(self=self, model='res.partner', input=partner)

        if product := args.get('product'):
            mutation['product_id'] = many2one(self=self, model='product.product', input=product)

        return mutation
