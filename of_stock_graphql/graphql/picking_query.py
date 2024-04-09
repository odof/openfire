# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .picking_type import Picking, PickingFilterInput


class PickingQuery(graphene.ObjectType):
    _name = 'PickingQuery'
    _type = 'query'

    pickings = graphene.List(
        graphene.NonNull(Picking),
        select=graphene.Argument(PickingFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_pickings(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['stock.picking']._prepare_graphql_domain(select=select, domain=domain)

        return env['stock.picking'].search(odoo_domain, offset=offset, limit=limit)
