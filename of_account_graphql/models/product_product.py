# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if 'taxes' in args.keys():
            mutation['taxes'] = x2many(self=self, model='account.tax', input=args.get('taxes'))

        return mutation
