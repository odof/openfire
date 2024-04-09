import graphene

from odoo.addons.graphql_base import OdooObjectType

from .company_type import Company


class User(OdooObjectType):
    _name = 'User'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    mobile = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    company = graphene.Field(Company, required=True, description="Company courante de l'utilisateur", name="company")
    companies = graphene.List(
        graphene.NonNull(Company),
        required=True,
        description="Liste des companys auquel à accès l'utilisateur",
    )

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None

    @staticmethod
    def resolve_companies(root, info):
        return root.company_ids or None


class UserInput(graphene.InputObjectType):
    _name = "UserInput"
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    mobile = graphene.String()
    phone = graphene.String()
    email = graphene.String()


class UserCreateInput(UserInput):
    _name = 'UserCreateInput'

    name = graphene.String(required=True)


class UserUpdateInput(UserInput):
    _name = 'UserUpdateInput'


class UserFilterInput(UserInput):
    _name = 'UserFilterInput'
