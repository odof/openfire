# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_account_graphql.graphql.account_tax_type import AccountTaxInput
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .planning_intervention_line import PlanningInterventionLine


class PlanningInterventionLineCreate(graphene.Mutation):
    _name = 'PlanningInterventionLineCreate'

    class Arguments:
        price_unit = graphene.NonNull(graphene.Float)
        name = graphene.String()
        discount = graphene.NonNull(graphene.Float)
        product = graphene.NonNull(ProductInput)
        quantity = graphene.NonNull(graphene.Float)
        taxes = graphene.NonNull(graphene.List(graphene.NonNull(AccountTaxInput)))

    Output = PlanningInterventionLine

    def mutate(
        self,
        info,
        **args,
    ):
        env = info.context['env']
        values = env['of.planning.intervention.line']._prepare_mutation_values(**args)
        return env['of.planning.intervention.line'].create(values)


class PlanningInterventionLineUpdate(graphene.Mutation):
    _name = 'PlanningInterventionLineUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        price_unit = graphene.NonNull(graphene.Float)
        name = graphene.String()
        discount = graphene.NonNull(graphene.Float)
        product = graphene.NonNull(ProductInput)
        quantity = graphene.NonNull(graphene.Float)
        taxes = graphene.NonNull(graphene.List(graphene.NonNull(AccountTaxInput)))

    Output = PlanningInterventionLine

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['of.planning.intervention.line']._prepare_mutation_values(**args)
        intervention = env['of.planning.intervention.line'].search([('id', '=', id)])
        intervention.write(values)
        return intervention


class PlanningInterventionLineDelete(graphene.Mutation):
    _name = 'PlanningInterventionLineDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningInterventionLine

    def mutate(self, info, id):
        env = info.context['env']

        return lazy_delete(env, 'of.plannoing.intervention.line', id)


class PlanningInterventionLineMutation(graphene.ObjectType):
    _name = 'PlanningInterventionLineMutation'
    _type = 'mutation'

    planning_intervention_line_update = PlanningInterventionLineUpdate.Field()
    planning_intervention_line_create = PlanningInterventionLineCreate.Field()
    planning_intervention_line_delete = PlanningInterventionLineDelete.Field()
