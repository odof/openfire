# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .partner_phone_type import PartnerPhone, PartnerPhoneInput
from .partner_title_type import PartnerTitle, PartnerTitleInput


class CompanyType(graphene.Enum):
    PERSON = "person"
    COMPANY = "company"


class Partner(OdooObjectType):
    _name = "Partner"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    lastname = graphene.String(description="Nom du partner")
    firstname = graphene.String(description="Prénom du partner")
    company_name = graphene.String(description="Nom de l'entreprise")
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
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    title = graphene.Field(PartnerTitleInput)
    parent = graphene.Field(lambda: PartnerInput)
    street = graphene.String()
    street2 = graphene.String()
    city = graphene.String()
    zip = graphene.String()
    email = graphene.String()
    of_phone_number_ids = graphene.List(graphene.NonNull(PartnerPhoneInput), name="phoneNumbers")
    write_date = graphene.DateTime()
    create_date = graphene.DateTime()
    company_type = graphene.Field(CompanyType)
    partner_latitude = graphene.Float()
    partner_longitude = graphene.Float()
    comment = graphene.String()
    ref = graphene.String()


class PartnerFilterInput(PartnerInput):
    _name = "PartnerFilterInput"
