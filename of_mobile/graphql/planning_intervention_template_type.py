# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_payment_graphql.graphql.of_payment_mode_type import PaymentMode, PaymentModeInput

from .planning_intervention_template_additional_line_type import (
    PlanningInterventionTemplateAdditionalLine,
    PlanningInterventionTemplateAdditionalLineInput,
)


class PlanningInterventionTemplate(OdooObjectType):
    _name = 'PlanningInterventionTemplate'
    _type = 'types'

    additional_line_ids = graphene.List(graphene.NonNull(PlanningInterventionTemplateAdditionalLine))
    send_reports = graphene.String(required=True)
    mobile_payment = graphene.Boolean()
    payment_mode_ids = graphene.List(graphene.NonNull(PaymentMode), name='paymentModes')
    auto_confirm_invoice = graphene.Boolean()
    mobile = graphene.Boolean()


class PlanningInterventionTemplateInput(graphene.InputObjectType):
    _name = 'PlanningInterventionTemplateInput'
    _type = 'types'

    additional_lines = graphene.List(graphene.NonNull(PlanningInterventionTemplateAdditionalLineInput))
    send_reports = graphene.String()
    mobile_payment = graphene.Boolean()
    payment_modes = graphene.List(graphene.NonNull(PaymentModeInput))
    auto_confirm_invoice = graphene.Boolean()
    mobile = graphene.Boolean()


class PlanningInterventionTemplateFilterInput(PlanningInterventionTemplateInput):
    _name = 'PlanningInterventionTemplateFilterInput'
