import graphene

from odoo.addons.graphql_base import OdooObjectType


class PartnerTitle(OdooObjectType):
    _name = 'PartnerTitle'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    used_for_phone = graphene.Boolean(required=True)

    @staticmethod
    def resolve_used_for_phone(root, info):
        return root.of_used_for_phone


class PartnerTitleInput(graphene.InputObjectType):
    _name = 'PartnerTitleInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    of_used_for_phone = graphene.Boolean(name='usedForPhone')


class PartnerTitleFilterInput(PartnerTitleInput):
    _name = 'PartnerTitleFilterInput'

    name = graphene.String(required=True)


class PartnerTitleCreateInput(PartnerTitleInput):
    _name = 'PartnerTitleCreateInput'

    name = graphene.String(required=True)


class PartnerTitleUpdateInput(PartnerTitleInput):
    _name = 'PartnerTitleUpdateInput'

    name = graphene.String(required=True)
