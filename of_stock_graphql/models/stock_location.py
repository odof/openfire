# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if warehouse := args.get('warehouse'):
            mutation['warehouse_id'] = many2one(self=self, model='stock.warehouse', input=warehouse)

        return mutation
