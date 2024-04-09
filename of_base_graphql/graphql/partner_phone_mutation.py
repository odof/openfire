import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .partner_phone_type import PartnerPhone, PartnerPhoneCreateInput, PartnerPhoneUpdateInput


class PartnerPhoneCreate(graphene.Mutation):
    _name = 'PartnerPhoneCreate'

    class Arguments:
        input = PartnerPhoneCreateInput(required=True)

    Output = PartnerPhone

    def mutate(self, info, input):
        env = info.context["env"]

        return lazy_create(env, 'of.res.partner.phone', input)


class PartnerPhoneUpdate(graphene.Mutation):
    _name = 'PartnerPhoneUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PartnerPhoneUpdateInput(required=True)

    Output = PartnerPhone

    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, 'of.res.partner.phone', id, input)


class PartnerPhoneDelete(graphene.Mutation):
    _name = 'PartnerPhoneDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PartnerPhone

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.res.product.phone', id)


class PartnerPhoneMutation(graphene.ObjectType):
    _name = 'PartnerPhoneMutation'
    _type = 'mutation'

    partner_phone_create = PartnerPhoneCreate.Field()
    partner_phone_update = PartnerPhoneUpdate.Field()
    partner_phone_delete = PartnerPhoneDelete.Field()
