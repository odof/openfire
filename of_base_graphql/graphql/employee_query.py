# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .employee_type import Employee, EmployeeFilterInput


class EmployeeQuery(graphene.ObjectType):
    _name = "EmployeeQuery"
    _type = "query"

    employees = graphene.List(
        graphene.NonNull(Employee),
        select=graphene.Argument(EmployeeFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_employees(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]

        odoo_domain = env["hr.employee"]._prepare_graphql_domain(select=select, domain=domain)

        return env["hr.employee"].search(odoo_domain, offset=offset, limit=limit)
