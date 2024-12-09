# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
        return root.sudo().company_id.id

    @staticmethod
    def resolve_authorized_company_ids(root, info):
        return root.user_id.sudo().company_ids.ids


class EmployeePlanningProgressDayResult(graphene.ObjectType):
    _name = "EmployeePlanningProgressDayResult"
    _type = "types"

    def __init__(self, day, value, max_value):
        self.day = day
        self.value = value
        self.max_value = max_value

    day = graphene.Date(required=True)
    value = graphene.Int(description="Progression du planning de l'employé pour cette journée", required=True)
    max_value = graphene.Int(description="Valeur maximale de progression pour cette journée", required=True)


class EmployeePlanningProgressResult(graphene.ObjectType):
    _name = "EmployeePlanningProgressResult"
    _type = "types"

    def __init__(self, days):
        self.days = days

    days = graphene.List(EmployeePlanningProgressDayResult, required=True)
