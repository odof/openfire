# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFEquipmentInterventionReportTemplate(models.Model):
    _inherit = "of.equipment.intervention.report.template"

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="of.equipment.intervention.report.template", domain=domain)

        if select:
            if select.id:
                odoo_domain += [("id", "=", select.id)]
            if select.name:
                odoo_domain += [("name", "like", select.name)]

        return odoo_domain

    def _prepare_mutation_values(self, **args):
        mutation = {}

        return mutation
