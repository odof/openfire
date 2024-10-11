# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="sale.order.template", domain=domain)

        if select:
            if select.id:
                odoo_domain += [("id", "=", select.id)]
            if select.name:
                odoo_domain += [("name", "like", select.name)]

        return odoo_domain

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        # Aujourd'hui, rien n'est prévu encore pour créer un modèle de devis depuis l'API graphql
        # cette méthode est juste là pour permettre l'ajout du modèle de devis sur un devis

        return mutation
