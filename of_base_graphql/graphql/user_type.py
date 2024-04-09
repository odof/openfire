import graphene

from odoo.addons.graphql_base import OdooObjectType

from .employee_type import Employee


class User(OdooObjectType):
    _name = 'User'
    _type = 'types'

    employee = graphene.Field(Employee)

    @staticmethod
    def resolve_employee(root, info):
        return root.employee_id or None
