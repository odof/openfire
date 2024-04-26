# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import convertImage


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if type := args.get('type'):
            mutation['type'] = type

        if res_model := args.get('res_model'):
            mutation['res_model'] = res_model

        if res_id := args.get('res_id'):
            mutation['res_id'] = res_id

        if attachment := input.get("datas", False):
            mutation['datas'] = convertImage(attachment)

        return mutation
