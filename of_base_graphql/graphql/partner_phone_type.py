import graphene

from odoo.addons.graphql_base import OdooObjectType

from .partner_title_type import PartnerTitle


class PartnerPhone(OdooObjectType):
    _name = 'PartnerPhone'
    _type = 'types'

    id = graphene.Int(required=True)
    type = graphene.String(required=True)
    number_display = graphene.String()
    title = graphene.Field(PartnerTitle)

    @staticmethod
    def resolve_title(root, info):
        return root.title_id or None


class PartnerPhoneInput(graphene.InputObjectType):
    _name = 'PartnerPhoneInput'
    _type = 'types'

    id = graphene.Int()
    type = graphene.String()
    number_display = graphene.String()
    title_id = graphene.Int()


class PartnerPhoneCreateInput(PartnerPhoneInput):
    _name = 'PartnerPhoneCreateInput'

    type = graphene.String(required=True)
    number_display = graphene.String(required=True)


class PartnerPhoneUpdateInput(PartnerPhoneInput):
    _name = 'PartnerPhoneUpdateInput'

    type = graphene.String(required=True)
    number_display = graphene.String(required=True)
