# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import convertImage
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if ttype := args.get('type'):
            mutation['type'] = ttype

        if res_model := args.get('res_model'):
            mutation['res_model'] = res_model

        if res_id := args.get('res_id'):
            mutation['res_id'] = res_id

        if attachment := args.get("datas", False):
            mutation['datas'] = convertImage(attachment)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='ir.attachment', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'ilike', select.name)]
            if select.res_model:
                odoo_domain += [('res_model', '=', select.res_model)]
            if select.res_id:
                odoo_domain += [('res_id', '=', select.res_id)]

        return odoo_domain
