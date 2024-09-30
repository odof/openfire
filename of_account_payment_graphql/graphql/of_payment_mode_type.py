# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_graphql.graphql.company_type import Company


class PaymentMode(OdooObjectType):
    _name = "PaymentMode"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String()
    shortname = graphene.String()
    company = graphene.Field(Company)

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None


class PaymentModeInput(graphene.InputObjectType):
    _name = "PaymentModeInput"
    _type = "types"

    id = graphene.Int()


class PaymentModeFilterInput(PaymentModeInput):
    _name = "PaymentModeFilterInput"
