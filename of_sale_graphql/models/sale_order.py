# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if date_order := args.get('date_order'):
            mutation['date_order'] = date_order

        if validity_date := args.get('validity_date'):
            mutation['validity_date'] = validity_date

        if partner := args.get('partner'):
            mutation['partner_id'] = many2one(self=self, model='res.partner', input=partner)

        if lines := args.get('lines'):
            mutation['order_line'] = x2many(self=self, model='sale.order.line', input=lines)

        return mutation
