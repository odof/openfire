import graphene

from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import AccountFiscalPositionInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .planning_intervention_task_type import PlanningInterventionTaskInput
from .planning_intervention_template_type import PlanningInterventionTemplate


class PlanningInterventionTemplateCreate(graphene.Mutation):
    _name = 'PlanningInterventionTemplateCreate'

    class Arguments:
        name = graphene.String()
        is_default_template = graphene.Boolean()
        task = graphene.Argument(PlanningInterventionTaskInput)
        fiscal_position = graphene.Argument(AccountFiscalPositionInput)

    Output = PlanningInterventionTemplate

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.planning.intervention.template']._prepare_mutation_values(**args)
        return env['of.planning.intervention.template'].create(values)


class PlanningInterventionTemplateUpdate(graphene.Mutation):
    _name = 'PlanningInterventionTemplateUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        is_default_template = graphene.Boolean()
        task = graphene.Argument(PlanningInterventionTaskInput)
        fiscal_position = graphene.Argument(AccountFiscalPositionInput)

    Output = PlanningInterventionTemplate

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.planning.intervention.template']._prepare_mutation_values(**args)
        template = env['of.planning.intervention.template'].search([('id', '=', id)])
        return template.write(values)


class PlanningInterventionTemplateDelete(graphene.Mutation):
    _name = 'PlanningInterventionTemplateDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningInterventionTemplate

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "of.planning.intervention.template", id)


class PlanningInterventionTemplateMutation(graphene.ObjectType):
    _name = 'PlanningInterventionTemplateMutation'
    _type = 'mutation'

    planning_intervention_template_create = PlanningInterventionTemplateCreate.Field()
    planning_intervention_template_update = PlanningInterventionTemplateUpdate.Field()
    planning_intervention_template_delete = PlanningInterventionTemplateDelete.Field()
