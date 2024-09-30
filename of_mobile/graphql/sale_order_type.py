# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_sale_management_template_graphql.graphql.sale_order_template_type import SaleOrderTemplate


class SaleOrder(OdooObjectType):
    _name = "SaleOrder"
    _type = "types"

    sale_template = graphene.Field(SaleOrderTemplate)
    signature_url = graphene.String()

    @staticmethod
    def resolve_sale_template(root, info):
        return root.sale_order_template_id or None

    @staticmethod
    def resolve_signature_url(root, info):
        return root.get_portal_url()
