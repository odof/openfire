# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_move_type import AccountMove
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningIntervention
from odoo.addons.of_sale_graphql.graphql.sale_order_type import SaleOrder


class PaymentType(graphene.Enum):
    INTERVENTION = 'intervention'
    SALE = 'sale'
    ALL = 'all'
    NONE = 'none'


class AccountPayment(OdooObjectType):
    _name = 'AccountPayment'
    _type = 'types'

    ttype = graphene.Field(PaymentType)
    intervention = graphene.Field(PlanningIntervention)
    invoice_intervention = graphene.Field(AccountMove)
    sale = graphene.Field(SaleOrder)
    invoice_sale = graphene.Field(AccountMove)

    @staticmethod
    def resolve_ttype(root, info):
        if root.of_intervention_id and root.of_sale_id:
            return 'all'
        if root.of_intervention_id:
            return 'intervention'
        elif root.of_sale_id:
            return 'sale'
        else:
            return 'none'

    @staticmethod
    def resolve_intervention(root, info):
        return root.of_intervention_id or None

    @staticmethod
    def resolve_invoice_intervention(root, info):
        return root.of_intervention_invoice_id or None

    @staticmethod
    def resolve_sale(root, info):
        return root.of_sale_id or None

    @staticmethod
    def resolve_invoice_sale(root, info):
        return root.of_sale_invoice_id or None
