# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_move_type import AccountMove
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import (
    PlanningIntervention,
    PlanningInterventionInput,
)


class PaymentType(graphene.Enum):
    INTERVENTION = 'intervention'
    SALE = 'sale'


class AccountPayment(OdooObjectType):
    _name = 'AccountPayment'
    _type = 'types'

    ttype = graphene.Field(PaymentType)
    intervention = graphene.Field(PlanningIntervention)
    invoice = graphene.Field(AccountMove)

    @staticmethod
    def resolve_ttype(root, info):
        if root.intervention_id:
            return 'intervention'
        else:
            return 'sale'

    @staticmethod
    def resolve_intervention(root, info):
        return root.intervention_id or None

    @staticmethod
    def resolve_invoice(root, info):
        return root.intervention_invoice_id or None


class AccountPaymentInput(graphene.InputObjectType):
    _name = "AccountPaymentInput"
    _type = 'types'

    ttype = graphene.Field(PaymentType)
    intervention = graphene.Field(PlanningInterventionInput)
