# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if partner := args.get('partner'):
            mutation['partner_id'] = many2one(self=self, model="res.partner", input=partner)

        if 'lines' in args.keys():
            mutation['move_ids_without_package'] = x2many(self=self, model='stock.move', input=args.get('lines'))

        if location := args.get('location'):
            mutation['location_id'] = many2one(self=self, model='stock.location', input=location)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='stock.picking', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
