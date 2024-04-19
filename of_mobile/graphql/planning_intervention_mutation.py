import graphene

from odoo.addons.of_equipment_graphql.graphql.equipment_mutation import EquipmentCreate, EquipmentUpdate
from odoo.addons.of_equipment_graphql.graphql.equipment_type import EquipmentInput
from odoo.addons.of_planning_graphql.graphql.planning_intervention_mutation import (
    PlanningInterventionCreate,
    PlanningInterventionUpdate,
)
from odoo.addons.of_survey_graphql.graphql.survey_mutation import SurveyCreate, SurveyUpdate
from odoo.addons.of_survey_graphql.graphql.survey_type import SurveyInput


class PlanningInterventionCreateMobile(PlanningInterventionCreate):
    _name = 'PlanningInterventionCreate'

    class Arguments(PlanningInterventionCreate.Arguments):
        equipments = graphene.List(graphene.NonNull(EquipmentInput))
        survey = SurveyInput()

    def mutate(self, info, input, **args):
        env = info.context["env"]
        create_equipments = env['of.equipment']
        equipments = []
        survey = False

        if args.get('survey', False):
            survey = args.pop('survey')

        if args.get('equipments', False):
            equipments = args.pop('equipments')

        intervention = PlanningInterventionCreate.mutate(self, info, input, **args)

        if survey:
            if survey.id:
                survey = SurveyUpdate().mutate(info, id=survey.id, input=survey)
            else:
                survey = SurveyCreate().mutate(info, input=survey)

        if survey:
            intervention.of_survey_id = survey.id

        for equipment in equipments:
            if equipment.id:
                equipment = EquipmentUpdate().mutate(info, id=equipment.id, input=equipment)
            else:
                equipment = EquipmentCreate().mutate(info, input=equipment)

            create_equipments += equipment

        if len(create_equipments) > 0:
            intervention.of_equipment_ids = [(6, 0, create_equipments.ids)]
            intervention.of_use_equipment = True

        return intervention


class PlanningInterventionUpdateMobile(PlanningInterventionUpdate):
    _name = 'PlanningInterventionUpdate'

    class Arguments(PlanningInterventionUpdate.Arguments):
        equipments = graphene.List(graphene.NonNull(EquipmentInput))
        survey = SurveyInput()

    def mutate(self, info, id, input, **args):
        env = info.context["env"]
        update_equipments = env['of.equipment']
        equipments = []
        survey = False

        if args.get('survey', False):
            survey = args.pop('survey')

        if args.get('equipments', False):
            equipments = args.pop('equipments')

        intervention = PlanningInterventionUpdate.mutate(self, info, id, input, **args)

        if survey:
            if survey.id:
                survey = SurveyUpdate().mutate(info, id=survey.id, input=survey)
            else:
                survey = SurveyCreate().mutate(info, input=survey)

        if survey:
            intervention.of_survey_id = survey.id

        for equipment in equipments:
            if equipment.id:
                equipment = EquipmentUpdate().mutate(info, id=equipment.id, input=equipment)
            else:
                equipment = EquipmentCreate().mutate(info, input=equipment)

            update_equipments += equipment

        if len(update_equipments) > 0:
            intervention.of_equipment_ids = [(6, 0, update_equipments.ids)]
            intervention.of_use_equipment = True

        return intervention


class PlanningInterventionMutation(graphene.ObjectType):
    _name = 'PlanningInterventionMutation'
    _type = 'mutation'

    planning_intervention_update = PlanningInterventionUpdateMobile.Field()
    planning_intervention_create = PlanningInterventionCreateMobile.Field()
