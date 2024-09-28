# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OfFluidType(models.Model):
    _inherit = "of.fluid.type"

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="of.fluid.type", domain=domain)

        if select:
            if select.id:
                odoo_domain += [("id", "=", select.id)]
            if select.name:
                odoo_domain += [("name", "like", select.name)]

        return odoo_domain

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        # Aujourd'hui, rien n'est prévu encore pour créer un type de fluide depuis l'API graphql
        # cette méthode est juste là pour permettre l'ajout du modèle de devis sur un devis

        return mutation
