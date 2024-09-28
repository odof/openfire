# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .fluid_type_type import FluidType, FluidTypeInput


class FluidTypeQuery(graphene.ObjectType):
    _name = "FluidTypeQuery"
    _type = "query"

    fluid_types = graphene.List(
        graphene.NonNull(FluidType),
        select=graphene.Argument(FluidTypeInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_fluid_types(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["of.fluid.type"]._prepare_graphql_domain(select=select, domain=domain)

        return env["of.fluid.type"].search(odoo_domain, offset=offset, limit=limit)
