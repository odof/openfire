import graphene

from odoo.addons.graphql_base import OdooObjectType


class Partner(OdooObjectType):
    _name = 'Partner'
    _type = 'types'

    request_address_ids = graphene.List(graphene.NonNull(lambda: Partner), name='requestAddress')
    request_partner_ids = graphene.List(graphene.NonNull(lambda: Partner), name="requestPartner")
