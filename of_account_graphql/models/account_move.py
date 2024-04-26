# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _prepare_mutation_values(self, input, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if partner := args.get('partner'):
            mutation['partner_id'] = many2one(self=self, model='res.partner', input=partner)

        if lines := args.get('lines'):
            mutation['invoice_line_ids'] = x2many(self=self, model='account.move.line', input=lines)

        if fiscal_position := args.get('fiscal_position'):
            mutation['fiscal_position_id'] = many2one(self=self, model='account.fiscal.position', input=fiscal_position)

        return mutation
