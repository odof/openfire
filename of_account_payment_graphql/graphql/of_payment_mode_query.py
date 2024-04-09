# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .of_payment_mode_type import PaymentMode, PaymentModeFilterInput


class PaymentModeQuery(graphene.ObjectType):
    _name = 'PaymentModeQuery'
    _type = 'query'

    payment_modes = graphene.List(
        graphene.NonNull(PaymentMode),
        select=graphene.Argument(PaymentModeFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_payment_modes(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['of.payment.mode']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.payment.mode'].search(odoo_domain, offset=offset, limit=limit)
