# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene


class CompanyType(graphene.Enum):
    PERSON = "person"
    COMPANY = "company"


class CompanyInput(graphene.InputObjectType):
    _name = "CompanyInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class CompanyFilterInput(CompanyInput):
    _name = "CompanyFilterInput"
