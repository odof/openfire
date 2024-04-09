# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from .planning_intervention_section_type import PlanningInterventionSection


class PlanningInterventionSectionUpdate(graphene.Mutation):
    _name = 'PlanningInterventionSectionUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        type = graphene.String()

    Output = PlanningInterventionSection

    def mutate(self, info, id, **args):
        env = info.context['env']
        section_obj = env['of.planning.intervention.section']
        values = section_obj._prepare_mutation_values(**args)
        planning_intervention_section = section_obj.search([('id', '=', id)])
        planning_intervention_section.write(values)
        return planning_intervention_section


class PlanningInterventionSectionMutation(graphene.ObjectType):
    _name = 'PlanningInterventionSectionMutation'
    _type = 'mutation'

    planning_intervention_section_update = PlanningInterventionSectionUpdate.Field()
