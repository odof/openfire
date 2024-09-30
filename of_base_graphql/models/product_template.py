# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get("name"):
            mutation["name"] = name

        if list_price := args.get("list_price"):
            mutation["list_price"] = list_price

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="product.template", domain=domain)

        if select:
            if select.name:
                odoo_domain += [("name", "ilike", select.name)]
            if select.ref:
                odoo_domain += [("ref", "ilike", select.ref)]

        return odoo_domain
