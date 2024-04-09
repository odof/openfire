import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .partner_phone_mutation import PartnerPhoneCreate, PartnerPhoneUpdate
from .partner_phone_type import PartnerPhoneInput
from .partner_title_mutation import PartnerTitleCreate, PartnerTitleUpdate
from .partner_title_type import PartnerTitleInput
from .partner_type import Partner, PartnerCreateInput, PartnerInput, PartnerUpdateInput


class PartnerCreate(graphene.Mutation):
    _name = 'PartnerCreate'

    class Arguments:
        input = PartnerCreateInput(required=True)
        phone_numbers = graphene.List(graphene.NonNull(PartnerPhoneInput))
        parent = PartnerInput()
        title = PartnerTitleInput()

    Output = Partner

    def mutate(self, info, input, phone_numbers=None, parent=None, title=None):
        env = info.context["env"]
        create_phone_numbers = env['of.res.partner.phone']

        if phone_numbers:
            for phone_number in phone_numbers:
                if phone_number.id:
                    # on est sur une mise à jour
                    phone_number = PartnerPhoneUpdate().mutate(info, id=phone_number.id, input=phone_number)
                else:
                    phone_number = PartnerPhoneCreate().mutate(info, input=phone_number)
                create_phone_numbers += phone_number

        if parent:
            if parent.id:
                parent = PartnerUpdate().mutate(info, id=parent.id, input=parent)
            else:
                parent = PartnerCreate().mutate(info, input=parent)

        if title:
            if title.id:
                title = PartnerTitleUpdate().mutate(info, id=title.id, input=title)
            else:
                title = PartnerTitleCreate().mutate(info, input=title)

        partner = lazy_create(env, "res.partner", input)

        if parent:
            partner.parent_id = parent.id

        if phone_numbers:
            partner.of_phone_numbers = [(6, 0, create_phone_numbers.ids)]

        if title:
            partner.title = title

        return partner


class PartnerUpdate(graphene.Mutation):
    _name = 'PartnerUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PartnerUpdateInput(required=True)
        phone_numbers = graphene.List(graphene.NonNull(PartnerPhoneInput))
        parent = PartnerInput()
        title = PartnerTitleInput()

    Output = Partner

    def mutate(self, info, id, input, phone_numbers=None, parent=None, title=None):
        env = info.context["env"]
        create_phone_numbers = env['of.res.partner.phone']

        if phone_numbers:
            for phone_number in phone_numbers:
                if phone_number.id:
                    # on est sur une mise à jour
                    phone_number = PartnerPhoneUpdate().mutate(info, id=phone_number.id, input=phone_number)
                else:
                    phone_number = PartnerPhoneCreate().mutate(info, input=phone_number)
                create_phone_numbers += phone_number

        if parent:
            if parent.id:
                parent = PartnerUpdate().mutate(info, id=parent.id, input=parent)
            else:
                parent = PartnerCreate().mutate(info, input=parent)

        if title:
            if title.id:
                title = PartnerTitleUpdate().mutate(info, id=title.id, input=title)
            else:
                title = PartnerTitleCreate().mutate(info, input=title)

        partner = lazy_update(env, "res.partner", id, input)

        if parent:
            partner.parent_id = parent.id

        if phone_numbers:
            partner.of_phone_number_ids = [(6, 0, create_phone_numbers.ids)]

        if title:
            partner.title = title

        return partner


class PartnerDelete(graphene.Mutation):
    _name = "PartnerDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = Partner

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'res.partner', id)


class PartnerMutation(graphene.ObjectType):
    _name = 'PartnerMutation'
    _type = 'mutation'

    partner_create = PartnerCreate.Field()
    partner_update = PartnerUpdate.Field()
    partner_delete = PartnerDelete.Field()
