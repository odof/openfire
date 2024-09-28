# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .fluid_type_type import FluidTypeInput
from .recovery_cylinder_type import RecoveryCylinder


class RecoveryCylinderCreate(graphene.Mutation):
    _name = "RecoveryCylinderCreate"

    class Arguments:
        name = graphene.String()
        fluid_type = graphene.Argument(FluidTypeInput)
        total_capacity = graphene.Float()

    Output = RecoveryCylinder

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["of.recovery.cylinder"]._prepare_mutation_values(**args)
        return env["of.recovery.cylinder"].create(values)


class RecoveryCylinderUpdate(graphene.Mutation):
    _name = "RecoveryCylinderUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        fluid_type = graphene.Argument(FluidTypeInput)
        total_capacity = graphene.Float()

    Output = RecoveryCylinder

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["of.recovery.cylinder"]._prepare_mutation_values(**args)
        recovery_cylinder = env["of.recovery.cylinder"].search([("id", "=", id)])
        recovery_cylinder.write(values)
        return recovery_cylinder


class RecoveryCylinderDelete(graphene.Mutation):
    _name = "RecoveryCylinderDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = RecoveryCylinder

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "of.recovery.cylinder", id)


class RecoveryCylinderMutation(graphene.ObjectType):
    _name = "RecoveryCylinderMutation"
    _type = "mutation"

    recovery_cylinder_create = RecoveryCylinderCreate.Field()
    recovery_cylinder_update = RecoveryCylinderUpdate.Field()
    recovery_cylinder_delete = RecoveryCylinderDelete.Field()
