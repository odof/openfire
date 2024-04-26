import logging

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .partner_phone_type import PartnerPhoneInput
from .partner_title_type import PartnerTitleInput
from .partner_type import CompanyType, Partner, PartnerInput

logger = logging.getLogger(__name__)


class PartnerCreate(graphene.Mutation):
    _name = 'PartnerCreate'

    class Arguments:
        name = graphene.String()
        title = graphene.Argument(PartnerTitleInput)
        parent = graphene.Argument(PartnerInput)
        street = graphene.String()
        street2 = graphene.String()
        city = graphene.String()
        zip = graphene.String()
        email = graphene.String()
        phone_numbers = graphene.List(PartnerPhoneInput)
        write_date = graphene.DateTime()
        create_date = graphene.DateTime()
        company_type = graphene.Argument(CompanyType)
        partner_latitude = graphene.Float()
        partner_longitude = graphene.Float()
        comment = graphene.String()
        ref = graphene.String()

    Output = Partner

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['res.partner']._prepare_mutation_values(**args)
        return env['res.partner'].create(values)


class PartnerUpdate(graphene.Mutation):
    _name = 'PartnerUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        title = graphene.Argument(PartnerTitleInput)
        parent = graphene.Argument(PartnerInput)
        street = graphene.String()
        street2 = graphene.String()
        city = graphene.String()
        zip = graphene.String()
        email = graphene.String()
        phone_numbers = graphene.List(PartnerPhoneInput)
        write_date = graphene.DateTime()
        create_date = graphene.DateTime()
        company_type = graphene.Argument(CompanyType)
        partner_latitude = graphene.Float()
        partner_longitude = graphene.Float()
        comment = graphene.String()
        ref = graphene.String()

    Output = Partner

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['res.partner']._prepare_mutation_values(**args)
        partner = env['res.partner'].search([('id', '=', id)])
        return partner.write(values)


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
