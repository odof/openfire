import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .partner_title_type import PartnerTitle, PartnerTitleCreateInput, PartnerTitleUpdateInput


class PartnerTitleCreate(graphene.Mutation):
    _name = 'PartnerTitleCreate'

    class Arguments:
        input = PartnerTitleCreateInput(required=True)

    Output = PartnerTitle

    def mutate(self, info, input):
        env = info.context["env"]

        return lazy_create(env, "res.partner.title", input)


class PartnerTitleUpdate(graphene.Mutation):
    _name = 'PartnerTitleUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PartnerTitleUpdateInput(required=True)

    Output = PartnerTitle

    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, "res.partner.title", id, input)


class PartnerTitleDelete(graphene.Mutation):
    _name = "PartnerTitleDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = PartnerTitle

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'res.partner.title', id)


class PartnerTitleMutation(graphene.ObjectType):
    _name = 'PartnerTitleMutation'
    _type = 'mutation'

    partner_title_create = PartnerTitleCreate.Field()
    partner_title_update = PartnerTitleUpdate.Field()
    partner_title_delete = PartnerTitleDelete.Field()
