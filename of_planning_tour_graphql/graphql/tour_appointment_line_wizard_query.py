# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from .tour_appointment_line_wizard_type import DayPeriod, TourAppointmentLineWizard


class TourAppointmentLineWizardQuery(graphene.ObjectType):
    _name = "TourAppointmentLineWizardQuery"
    _type = "query"

    tour_appointment_line_wizard = graphene.List(
        graphene.NonNull(TourAppointmentLineWizard),
        required=True,
        partner_id=graphene.Int(required=True),
        partner_address_id=graphene.Int(required=True),
        employee_ids=graphene.List(graphene.Int, required=True),
        day_period=DayPeriod(required=True),
        task_id=graphene.Int(required=True),
        duration=graphene.Float(required=True),
        start_search_date=graphene.DateTime(required=True),
        search_period_in_days=graphene.Int(required=True),
        company_id=graphene.Int(required=True),
        description="Recherche des créneaux de rendez-vous disponible pour une liste d'employés",
    )

    @staticmethod
    def resolve_tour_appointment_line_wizard(
        root,
        info,
        partner_id,
        partner_address_id,
        employee_ids,
        day_period,
        task_id,
        duration,
        start_search_date,
        search_period_in_days,
        company_id,
    ):
        env = info.context["env"]
        wizard = env["of.tour.appointment.wizard"].create(
            {
                "partner_id": partner_id,
                "partner_address_id": partner_address_id,
                "company_id": company_id,
                "task_id": task_id,
                "duration": duration,
                "day_period": day_period.value,
                "start_date_search": start_search_date,
                "search_period_in_days": search_period_in_days,
                "pre_employee_ids": employee_ids,
            }
        )
        wizard._populate_line_ids()
        return wizard.line_ids
