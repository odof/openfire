import logging

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .partner_phone_type import PartnerPhone
from .partner_title_type import PartnerTitle

logger = logging.getLogger(__name__)


class CompanyType(graphene.Enum):
    PERSON = 'person'
    COMPANY = 'company'


class Partner(OdooObjectType):
    _name = 'Partner'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    customer = graphene.Boolean()
    title = graphene.Field(PartnerTitle)
    parent = graphene.Field(lambda: Partner)
    street = graphene.String()
    street2 = graphene.String()
    city = graphene.String()
    zip = graphene.String()
    email = graphene.String()
    of_phone_number_ids = graphene.List(graphene.NonNull(PartnerPhone), required=True, name="phoneNumbers")
    write_date = graphene.DateTime()
    create_date = graphene.DateTime()
    company_type = graphene.Field(CompanyType, required=True)
    partner_latitude = graphene.Float()
    partner_longitude = graphene.Float()
    comment = graphene.String()
    ref = graphene.String()

    @staticmethod
    def resolve_title(root, info):
        return root.title or None

    def resolve_parent(root, info):
        return root.parent_id or None


class PartnerInput(graphene.InputObjectType):
    _name = "PartnerInput"
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    city = graphene.String()
    comment = graphene.String()
    email = graphene.String()
    street = graphene.String()
    street2 = graphene.String()
    zip = graphene.String()
    customer = graphene.Boolean()
    write_date = graphene.DateTime()
    create_date = graphene.DateTime()
    company_type = graphene.Field(CompanyType)
    partner_latitude = graphene.Float()
    partner_longitude = graphene.Float()


class PartnerCreateInput(PartnerInput):
    _name = 'PartnerCreateInput'

    name = graphene.String(required=True)


class PartnerUpdateInput(PartnerInput):
    _name = 'PartnerUpdateInput'


class PartnerFilterInput(PartnerInput):
    _name = 'PartnerFilterInput'
