# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from dateutil.relativedelta import relativedelta

from odoo import fields

from .planning_intervention_type import PlanningInterventionsOffline


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

    @staticmethod
    def resolve_planning_interventions_offline(root, info, update_date=None, local_intervention_ids=None):
        env = info.context["env"]
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

        odoo_domain += [
            ('start', '>=', fields.Date.to_string(before)),
            ('start', '<=', fields.Date.to_string(after)),
            ('of_state', 'not in', ['cancel', 'postponed']),
        ]

        if update_date:
            odoo_domain += [('of_update_date', '>=', fields.Datetime.to_string(update_date))]

        interventions = env['calendar.event'].search(odoo_domain)

        result = _PlanningInterventionsOfflineResult()
        result.interventions = interventions or []

        # ajouter ici la logique pour renvoyer la liste des interventions a supprimer
        return result
