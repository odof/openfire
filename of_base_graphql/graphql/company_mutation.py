import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_update

from .company_type import Company, CompanyCreateInput, CompanyUpdateInput


class CompanyCreate(graphene.Mutation):
    _name = 'CompanyCreate'

    class Arguments:
        input = CompanyCreateInput(required=True)

    Output = Company

    def mutate(self, info, input):
        env = info.context["env"]

        return lazy_create(env, "res.company", input)


class CompanyUpdate(graphene.Mutation):
    _name = 'CompanyUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = CompanyUpdateInput(required=True)

    Output = Company

    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, "res.company", id, input)


class CompanyMutation(graphene.ObjectType):
    _name = 'CompanyMutation'
    _type = 'mutation'

    company_create = CompanyCreate.Field()
    company_update = CompanyUpdate.Field()
