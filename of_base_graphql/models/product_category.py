# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get("name"):
            mutation["name"] = name

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="product.category", domain=domain)

        if select:
            if select.name:
                odoo_domain += [("name", "ilike", select.name)]
            if select.id:
                odoo_domain += [("id", "=", select.id)]

        return odoo_domain
