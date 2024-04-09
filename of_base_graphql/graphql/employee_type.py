# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class Employee(OdooObjectType):
    _name = 'Employee'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    mobile_phone = graphene.String(default_value="")
    work_phone = graphene.String(default_value="")
    work_email = graphene.String(default_value="")


class EmployeeInput(graphene.InputObjectType):
    _name = "EmployeeInput"
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    mobile_phone = graphene.String()
    work_phone = graphene.String()
    work_email = graphene.String()
    company_id = graphene.Int()


class EmployeeFilterInput(EmployeeInput):
    _name = 'EmployeeFilterInput'


class EmployeeCreateInput(EmployeeInput):
    _name = 'EmployeeCreateInput'


class EmployeeUpdateInput(EmployeeInput):
    _name = 'EmployeeUpdateInput'
