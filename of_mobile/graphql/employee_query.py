# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

import graphene

from odoo.addons.of_base_graphql.graphql.employee_type import Employee

from .employee_type import EmployeePlanningProgressDayResult, EmployeePlanningProgressResult


class EmployeeQuery(graphene.ObjectType):
    _name = "EmployeeQuery"
    _type = "query"

    employees_field_workers = graphene.List(
        graphene.NonNull(Employee),
        description="Retourne pour une company donnée, les travailleurs de terrain",
        company_id=graphene.Int(required=True),
    )
    employee_planning_progress = graphene.Field(
        graphene.NonNull(EmployeePlanningProgressResult),
        description="Retourne pour une company donnée, les employés ayant un planning en cours",
        employee_id=graphene.Int(required=True),
        start_day=graphene.Date(
            required=True, description="Date à partir de laquelle on veut connaitre la disponibilité de l'employé"
        ),
        days=graphene.Int(required=True, description="Nombre de jours à partir de la date de début"),
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

    @staticmethod
    def resolve_employee_planning_progress(root, info, employee_id, start_day, days):
        env = info.context["env"]

        # retourner le résultat de la méthode planning_progress_bar présente sur le modèle of.calendar.event
        # pour cet employé
        employee = env["hr.employee"].browse(employee_id)

        i = 0

        day_results = []
        while i < days:
            current_day = start_day + timedelta(days=i)
            current_day_str = current_day.strftime("%Y-%m-%d")
            date_start_str = current_day_str + " 00:00:01"
            date_stop_str = current_day_str + " 23:59:59"
            res = env["calendar.event"].planning_progress_bar(
                fields=["of_resource_id"],
                res_ids={"of_resource_id": [employee.id]},
                date_start_str=date_start_str,
                date_stop_str=date_stop_str,
            )
            resource = res["of_resource_id"][employee.id]
            day_results.append(
                EmployeePlanningProgressDayResult(
                    day=current_day,
                    value=resource["value"],
                    max_value=resource["max_value"],
                )
            )
            i += 1
        return EmployeePlanningProgressResult(days=day_results)
