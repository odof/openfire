# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFPlanningInterventionSection(models.Model):
    _name = 'of.planning.intervention.section'
    _description = "Sections to display on mobile"
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    ttype = fields.Char(string="Type", required=True)

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if ttype := args.get('type'):
            mutation['ttype'] = ttype

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.planning.intervention.section', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
