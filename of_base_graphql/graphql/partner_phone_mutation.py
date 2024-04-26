import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .partner_phone_type import PartnerPhone
from .partner_title_type import PartnerTitleInput


class PartnerPhoneCreate(graphene.Mutation):
    _name = 'PartnerPhoneCreate'

    class Arguments:
        type = graphene.String()
        number_display = graphene.String()
        title = graphene.Argument(PartnerTitleInput)

    Output = PartnerPhone

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.res.partner.phone']._prepare_mutation_values(**args)
        return env['of.res.partner.phone'].create(values)


class PartnerPhoneUpdate(graphene.Mutation):
    _name = 'PartnerPhoneUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        type = graphene.String()
        number_display = graphene.String()
        title = graphene.Argument(PartnerTitleInput)

    Output = PartnerPhone

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.res.partner.phone']._prepare_mutation_values(**args)
        phone = env['of.res.partner.phone'].search([('id', '=', id)])
        return phone.write(values)


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
