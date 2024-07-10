# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene
from dateutil.relativedelta import relativedelta

from odoo import fields

from .planning_intervention_type import PlanningIntervention, PlanningInterventionsOffline


class _PlanningInterventionsOfflineResult:
    interventions = []
    interventions_to_delete = []


class PlanningInterventionQuery(graphene.ObjectType):
    _name = 'PlanningInterventionQuery'
    _type = 'query'

    planning_interventions_offline = graphene.Field(
        PlanningInterventionsOffline,
        local_intervention_ids=graphene.List(
            graphene.NonNull(graphene.Int),
            description="""Liste des identifiants d'interventions présent en local
                sur le client cherchant à se synchroniser""",
        ),
        update_date=graphene.DateTime(),
    )

    planning_interventions_preview = graphene.List(
        graphene.NonNull(PlanningIntervention),
        description="""Permet de récupérer la liste des interventions
        pour un ensemble de techniciens sur une période donnée""",
        employee_id=graphene.Int(required=True),
        starting_date=graphene.Date(required=True, description="Jour à partir duquel récupérer les interventions"),
        number_of_days=graphene.Int(required=True, description="Nombre de jour à récupérer après la date"),
    )

    @staticmethod
    def resolve_planning_interventions_offline(root, info, update_date=None, local_intervention_ids=None):
        env = info.context['env']
        odoo_domain = []

        display_planning_days_before = (
            env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_before')
        )

        display_planning_days_after = (
            env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_after')
        )

        today = fields.Date.from_string(fields.Date.today())
        before = today + relativedelta(days=-int(display_planning_days_before))
        after = today + relativedelta(days=int(display_planning_days_after))

        original_domain = [
            ('of_employee_ids.user_id', '=', env.user.id),
            ('start', '>=', fields.Date.to_string(before)),
            ('start', '<=', fields.Date.to_string(after)),
            ('of_state', 'not in', ['cancel', 'postponed']),
        ]

        odoo_domain += original_domain

        if update_date:
            odoo_domain += [('of_update_date', '>=', fields.Datetime.to_string(update_date))]

        interventions = env['calendar.event'].search(odoo_domain)

        result = _PlanningInterventionsOfflineResult()
        result.interventions = [inter for inter in interventions] or []
        result.interventions_to_delete = []
        # Dans le cas où le mobile fourni sa dernière date de maj et
        # ses interventions présentes en local
        # on va le notifier de la liste des interventions qu'il n'a plus a garder

        if update_date:
            local_intervention_ids = local_intervention_ids or []
            # On va rechercher toutes les interventions sur la période de synchro
            synchronizable_interventions = env['calendar.event'].search(original_domain)

            for inter in synchronizable_interventions:
                # si l'intervention n'est pas dans la liste des locales,
                # cela doit etre une nouvelle intervention
                # on va donc l'ajouter à la liste des nouvelles interventions
                if inter.id not in local_intervention_ids and inter not in result.interventions:
                    result.interventions.append(inter)

            result.interventions_to_delete.extend(
                local_intervention
                for local_intervention in local_intervention_ids
                if local_intervention not in synchronizable_interventions.ids
            )
        return result

    @staticmethod
    def resolve_planning_interventions_preview(root, info, employee_id, starting_date, number_of_days):
        env = info.context['env']

        after = starting_date + relativedelta(days=int(number_of_days))

        domain = [
            ('of_employee_ids', 'in', employee_id),
            ('start', '>=', fields.Date.to_string(starting_date)),
            ('start', '<=', fields.Date.to_string(after)),
            ('of_state', 'not in', ['cancel', 'postponed']),
        ]

        return env['calendar.event'].search(domain) or []
