# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .recovery_cylinder_type import RecoveryCylinder, RecoveryCylinderInput


class RecoveryCylinderQuery(graphene.ObjectType):
    _name = "RecoveryCylinderQuery"
    _type = "query"

    recovery_cylinders = graphene.List(
        graphene.NonNull(RecoveryCylinder),
        select=graphene.Argument(RecoveryCylinderInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_recovery_cylinders(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["of.recovery.cylinder"]._prepare_graphql_domain(select=select, domain=domain)

        return env["of.recovery.cylinder"].search(odoo_domain, offset=offset, limit=limit)
