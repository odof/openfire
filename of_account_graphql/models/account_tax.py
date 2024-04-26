# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AcccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if amount := args.get('amount'):
            mutation['amount'] = amount

        if 'price_include' in args.keys():
            mutation['price_include'] = args['price_include']

        return mutation
