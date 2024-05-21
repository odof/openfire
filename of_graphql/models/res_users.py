# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if mobile := args.get('mobile'):
            mutation['mobile'] = mobile

        if phone := args.get('phone'):
            mutation['phone'] = phone

        if email := args.get('email'):
            mutation['email'] = email

        if company := args.get('company'):
            mutation['company_id'] = many2one(self=self, model='res.company', input=company)

        if companies := args.get('companies'):
            mutation['company_ids'] = x2many(self=self, model='res.company', input=companies)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='res.users', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'ilike', select.name)]
            if select.email:
                odoo_domain += [('email', 'ilike', select.email)]
            if select.mobile:
                odoo_domain += [('mobile', 'ilike', select.mobile)]
            if select.phone:
                odoo_domain += [('phone', 'ilike', select.phone)]

        return odoo_domain
