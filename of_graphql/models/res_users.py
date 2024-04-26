# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


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
            mutation['company'] = many2one(self=self, model='res.company', input=company)

        if companies := args.get('companies'):
            mutation['companies'] = x2many(self=self, model='res.company', input=companies)

        return mutation
