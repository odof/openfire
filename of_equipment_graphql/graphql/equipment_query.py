# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .equipment_type import Equipment, EquipmentFilterInput


class EquipmentQuery(graphene.ObjectType):
    _name = 'EquipmentQuery'
    _type = 'query'

    equipments = graphene.List(
        graphene.NonNull(Equipment),
        select=graphene.Argument(EquipmentFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_equipments(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env['of.equipment']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.equipment'].search(odoo_domain, offset=offset, limit=limit)
