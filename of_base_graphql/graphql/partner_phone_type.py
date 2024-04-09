# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .partner_title_type import PartnerTitle, PartnerTitleInput


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
    title = graphene.Field(PartnerTitleInput)
