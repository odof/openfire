# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class Partner(OdooObjectType):
    _name = 'Partner'
    _type = 'types'

    request_address_ids = graphene.List(graphene.NonNull(lambda: Partner), name='requestAddress')
    request_partner_ids = graphene.List(graphene.NonNull(lambda: Partner), name="requestPartner")


class PartnerInput(graphene.InputObjectType):
    _name = 'PartnerInput'
    _type = 'types'

    request_address_ids = graphene.List(graphene.NonNull(lambda: PartnerInput), name='requestAddress')
    request_partner_ids = graphene.List(graphene.NonNull(lambda: PartnerInput), name="requestPartner")
