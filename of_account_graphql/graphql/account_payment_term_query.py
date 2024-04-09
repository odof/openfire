# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .account_payment_term_type import AccountPaymentTerm, AccountPaymentTermFilterInput


class AccountPaymentTermQuery(graphene.ObjectType):
    _name = 'AccountPaymentTermQuery'
    _type = 'query'

    account_payment_terms = graphene.List(
        graphene.NonNull(AccountPaymentTerm),
        select=graphene.Argument(AccountPaymentTermFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_account_payment_terms(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['account.payment.term']._prepare_graphql_domain(select=select, domain=domain)

        return env['account.payment.term'].search(odoo_domain, offset=offset, limit=limit)
