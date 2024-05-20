# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFImage(models.Model):
    _inherit = 'of.image'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if caption := args.get('caption'):
            mutation['caption'] = caption

        if printable := args.get('printable'):
            mutation['printable'] = printable

        if sequence := args.get('sequence'):
            mutation['sequence'] = sequence

        if image_1920 := args.get('image_1920'):
            mutation['image_1920'] = image_1920

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='res.company', domain=domain)

        if select:
            if select.name:
                odoo_domain += [('name', 'ilike', select.name)]
            if select.id:
                odoo_domain += [('id', '=', select.id)]

        return odoo_domain
