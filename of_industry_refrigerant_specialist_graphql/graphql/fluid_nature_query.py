# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .fluid_nature_type import FluidNature, FluidNatureInput


class FluidNatureQuery(graphene.ObjectType):
    _name = "FluidNatureQuery"
    _type = "query"

    fluid_natures = graphene.List(
        graphene.NonNull(FluidNature),
        select=graphene.Argument(FluidNatureInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_fluid_natures(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["of.fluid.nature"]._prepare_graphql_domain(select=select, domain=domain)

        return env["of.fluid.nature"].search(odoo_domain, offset=offset, limit=limit)
