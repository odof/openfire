# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_account_payment_graphql.graphql.account_payment_type import AccountPayment, PaymentModeInput
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningInterventionInput

from .account_payment_type import PaymentType


class PaymentInterventionCreate(graphene.Mutation):
    _name = "PaymentInterventionCreate"

    class Arguments:
        intervention = PlanningInterventionInput(required=True)
        amount = graphene.Float(required=True)
        date = graphene.DateTime()
        partner = PartnerInput()
        ttype = PaymentType(required=True)
        mode = PaymentModeInput(required=True)
        payment_reference = graphene.String()

    Output = AccountPayment

    def mutate(self, info, **args):
        env = info.context["env"]

        payment_obj = env["account.payment"]
        payment = payment_obj.create_payment_intervention(**args)

        return payment or None


class PaymentInterventionCreateMutation(graphene.ObjectType):
    _name = "PaymentInterventionCreateMutation"
    _type = "mutation"

    payment_intervention_create = PaymentInterventionCreate.Field()
