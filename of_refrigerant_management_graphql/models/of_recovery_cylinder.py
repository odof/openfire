# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class RecoveryCylinder(models.Model):
    _inherit = "of.recovery.cylinder"

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="of.recovery.cylinder", domain=domain)

        if select:
            if select.id:
                odoo_domain += [("id", "=", select.id)]
            if select.name:
                odoo_domain += [("name", "like", select.name)]

        return odoo_domain

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get("name"):
            mutation["name"] = name

        if fluid_type := args.get("fluid_type"):
            mutation["fluid_type_id"] = many2one(self=self, model="of.fluid.type", input=fluid_type)

        if total_capacity := args.get("total_capacity"):
            mutation["total_capacity"] = total_capacity

        return mutation
