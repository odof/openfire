# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_base_graphql.graphql.employee_type import Employee


class EmployeeQuery(graphene.ObjectType):
    _name = "EmployeeQuery"
    _type = "query"

    employees_field_workers = graphene.List(
        graphene.NonNull(Employee),
        description="Retourne pour une company donnée, les travailleurs de terrain",
        company_id=graphene.Int(required=True),
    )

    @staticmethod
    def resolve_employees_field_workers(root, info, company_id):
        env = info.context["env"]

        domain = [
            "|",
            ["of_is_operator", "=", True],
            ["of_is_salesperson", "=", True],
        ]

        return env["hr.employee"].with_company(company_id).search(domain)
