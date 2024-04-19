# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class Employee(OdooObjectType):
    _name = "Employee"
    _type = "types"

    company_id = graphene.Int()

    # On ne retourne qu'une liste d'identifiants de company
    # pour des raisons de sécurité car on va devoir faire un sudo
    authorized_company_ids = graphene.List(
        graphene.NonNull(graphene.Int),
        description="Liste des ids sur lesquelles l'employé est autorisé",
    )

    @staticmethod
    def resolve_company_id(root, info):
        return root.user_id.sudo().company_id.id

    @staticmethod
    def resolve_authorized_company_ids(root, info):
        return root.user_id.sudo().company_ids.ids
