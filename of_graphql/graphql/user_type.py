# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput

from ..graphql.company_type import Company


class User(OdooObjectType):
    _name = 'User'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    mobile = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    company = graphene.Field(Company, required=True, description="Société courante de l'utilisateur", name="company")
    companies = graphene.List(
        graphene.NonNull(Company),
        required=True,
        description="Liste des sociétés auxquelles à accès l'utilisateur",
    )

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None

    @staticmethod
    def resolve_companies(root, info):
        return root.company_ids or None


class UserInput(graphene.InputObjectType):
    _name = 'UserInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    mobile = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    company = graphene.Field(
        CompanyInput, required=True, description="Société courante de l'utilisateur", name="company"
    )
    companies = graphene.List(
        graphene.NonNull(CompanyInput),
        required=True,
        description="Liste des sociétés auxquelles à accès l'utilisateur",
    )


class UserFilterInput(UserInput):
    _name = 'UserFilterInput'
