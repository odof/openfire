# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class Product(models.Model):
    _inherit = 'product.product'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if brand := args.get('brand'):
            mutation['brand_id'] = many2one(self=self, model='of.product.brand', input=brand)

        return mutation
