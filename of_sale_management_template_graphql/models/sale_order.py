# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if template := args.get('sale_template'):
            mutation['sale_order_template_id'] = many2one(self=self, model='sale.order.template', input=template)
        return mutation
