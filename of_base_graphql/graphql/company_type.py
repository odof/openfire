import graphene

from odoo.addons.graphql_base import OdooObjectType


class CompanyType(graphene.Enum):
    PERSON = 'person'
    COMPANY = 'company'


class Company(OdooObjectType):
    _name = "Company"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class CompanyInput(graphene.InputObjectType):
    _name = "CompanyInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class CompanyUpdateInput(CompanyInput):
    _name = "CompanyUpdateInput"


class CompanyCreateInput(CompanyInput):
    _name = "CompanyCreateInput"


class CompanyFilterInput(CompanyInput):
    _name = "CompanyFilterInput"
