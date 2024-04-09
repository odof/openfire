# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.employee_type import EmployeeInput


class Employee(OdooObjectType):
    _name = 'Employee'
    _type = 'types'

    of_is_operator = graphene.Boolean(required=True, name='isOperator')
    of_is_salesperson = graphene.Boolean(required=True, name='isSalesperson')


class EmployeeFilterInput(EmployeeInput):
    _name = 'EmployeeFilterInput'
    _type = 'types'

    is_operator = graphene.Boolean()
    is_salesperson = graphene.Boolean()
