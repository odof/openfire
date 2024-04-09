# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if partner := args.get('partner'):
            mutation['partner_id'] = many2one(self=self, model='res.partner', input=partner)

        if amount := args.get('amount'):
            mutation['amount'] = amount

        if payment_state := args.get('payment_state'):
            mutation['payment_state'] = payment_state

        if date := args.get('date'):
            mutation['date'] = date

        if payment_mode := args.get('payment_mode'):
            mutation['of_payment_mode_id'] = many2one(self=self, model='of.payment.mode', input=payment_mode)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='account.payment', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
