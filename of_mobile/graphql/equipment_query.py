# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.models import expression

from odoo.addons.of_equipment_graphql.graphql.equipment_type import Equipment


class EquipmentQuery(graphene.ObjectType):
    _name = "EquipmentQuery"
    _type = "query"

    equipments_search = graphene.List(
        graphene.NonNull(Equipment),
        partner_ids=graphene.List(graphene.NonNull(graphene.Int), required=True),
        query=graphene.String(),
    )

    @staticmethod
    def resolve_equipments_search(root, info, partner_ids, query=None):
        env = info.context["env"]
        domain = []
        if not partner_ids:
            return domain

        for partner_id in partner_ids:
            domain = expression.OR(
                [
                    domain,
                    [
                        "|",
                        ("customer_id", "=", partner_id),
                        ("site_address_id", "=", partner_id),
                    ],
                ],
            )

        if query:
            domain = expression.AND([domain, ["|", ("name", "ilike", query), ("product_id.name", "ilike", query)]])

        return env["of.equipment"].search(domain)
