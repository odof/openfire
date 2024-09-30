# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class ResPartnerTitle(models.Model):
    _inherit = "res.partner.title"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get("name"):
            mutation["name"] = name

        if "of_used_for_phone" in args:
            mutation["of_used_for_phone"] = args["of_used_for_phone"]

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="res.partner.title", domain=domain)

        if select:
            if select.name:
                odoo_domain += [("name", "ilike", select.name)]
            if select.used_for_phone:
                odoo_domain += [("of_used_for_phone", "=", select.used_for_phone)]

        return odoo_domain
