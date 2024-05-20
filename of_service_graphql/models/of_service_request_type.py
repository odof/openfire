# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OSServcieRequestType(models.Model):
    _inherit = 'of.service.request.type'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if 'stages' in args.keys():
            mutation['stage_ids'] = x2many(self=self, model='of.service.request.type', input=args.get('stages'))

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.service.request', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
