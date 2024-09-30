# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_graphql.graphql.company_type import Company


class AccountPaymentTerm(OdooObjectType):
    _name = "AccountPaymentTerm"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    company = graphene.Field(Company)

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None


class AccountPaymentTermInput(graphene.InputObjectType):
    _name = "AccountPaymentTermInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    company = graphene.Field(CompanyInput)


class AccountPaymentTermFilterInput(AccountPaymentTermInput):
    _name = "AccountPaymentTermFilterInput"
