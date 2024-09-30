# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .employee_type import Employee, EmployeeInput


class User(OdooObjectType):
    _name = "User"
    _type = "types"

    employee = graphene.Field(Employee)

    @staticmethod
    def resolve_employee(root, info):
        return root.employee_id or None


class UserInput(graphene.InputObjectType):
    _name = "UserInput"
    _type = "types"

    employee = EmployeeInput()
