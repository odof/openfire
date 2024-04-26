# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class OSServcieRequestType(models.Model):
    _inherit = 'of.service.request.type'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if stages := args.get('stages'):
            mutation['stage_ids'] = x2many(self=self, model='of.service.request.type', input=stages)

        return mutation
