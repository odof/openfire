# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningInterventionInput
from odoo.addons.of_sale_graphql.graphql.sale_order_type import SaleOrderInput

from ..graphql.account_payment_type import AccountPayment, AccountPaymentInput, PaymentType
from ..graphql.configuration_query import ConfigurationQuery
from ..graphql.configuration_type import Configuration
from ..graphql.employee_query import EmployeeQuery
from ..graphql.employee_type import Employee
from ..graphql.fcm_token_mutation import FCMTokenMutation
from ..graphql.fcm_token_type import FCMToken, FCMTokenInput
from ..graphql.partner_query import PartnerQuery
from ..graphql.partner_type import PartnerCheckDuplications
from ..graphql.planning_intervention_mutation import PlanningInterventionSendReportMutation
from ..graphql.planning_intervention_query import PlanningInterventionQuery, PlanningInterventionsOffline
from ..graphql.planning_intervention_section_mutation import PlanningInterventionSectionMutation
from ..graphql.planning_intervention_section_query import PlanningInterventionSectionQuery
from ..graphql.planning_intervention_section_type import (
    PlanningInterventionSection,
    PlanningInterventionSectionFilterInput,
    PlanningInterventionSectionInput,
)
from ..graphql.planning_intervention_task_type import (
    PlanningInterventionTask,
    PlanningInterventionTaskFilterInput,
    PlanningInterventionTaskInput,
)
from ..graphql.planning_intervention_template_additional_line_type import (
    PlanningInterventionTemplateAdditionalLine,
    PlanningInterventionTemplateAdditionalLineFilterInput,
    PlanningInterventionTemplateAdditionalLineInput,
)
from ..graphql.planning_intervention_template_type import (
    PlanningInterventionTemplate,
    PlanningInterventionTemplateFilterInput,
    PlanningInterventionTemplateInput,
)
from ..graphql.planning_intervention_type import PlanningIntervention
from ..graphql.product_query import ProductQuery
from ..graphql.sale_order_template_type import SaleOrderTemplate, SaleOrderTemplateFilterInput, SaleOrderTemplateInput
from ..graphql.sale_order_type import SaleOrder
from ..graphql.user_type import User, UserInput


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_mobile_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Configuration,
                User,
                UserInput,
                PartnerCheckDuplications,
                PlanningInterventionQuery,
                ConfigurationQuery,
                PartnerQuery,
                ProductQuery,
                PlanningInterventionsOffline,
                PlanningIntervention,
                PlanningInterventionSendReportMutation,
                PlanningInterventionSectionQuery,
                PlanningInterventionSection,
                PlanningInterventionSectionInput,
                PlanningInterventionSectionFilterInput,
                PlanningInterventionSectionMutation,
                EmployeeQuery,
                Employee,
                FCMTokenMutation,
                FCMToken,
                FCMTokenInput,
                PlanningInterventionTemplate,
                PlanningInterventionTemplateInput,
                PlanningInterventionTemplateFilterInput,
                PlanningInterventionTemplateAdditionalLine,
                PlanningInterventionTemplateAdditionalLineFilterInput,
                PlanningInterventionTemplateAdditionalLineInput,
                AccountPayment,
                AccountPaymentInput,
                SaleOrder,
                PlanningInterventionTask,
                PlanningInterventionTaskInput,
                PlanningInterventionTaskFilterInput,
                SaleOrderTemplate,
                SaleOrderTemplateInput,
                SaleOrderTemplateFilterInput,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            'UserMutation': {
                'user_update': {
                    'fcm_tokens': FCMTokenInput,
                },
            },
            'AccountPaymentMutation': {
                'account_payment_create': {
                    'ttype': PaymentType,
                    'intervention': PlanningInterventionInput,
                    'sale': SaleOrderInput,
                },
                'account_payment_update': {
                    'ttype': PaymentType,
                    'intervention': PlanningInterventionInput,
                    'sale': SaleOrderInput,
                },
            },
            'PlanningInterventionMutation': {
                'planning_intervention_create': {
                    'additional_sale': SaleOrderInput,
                },
                'planning_intervention_update': {
                    'additional_sale': SaleOrderInput,
                },
            },
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
