# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.attachment_type import Attachment, AttachmentInput
from ..graphql.partner_type import Partner, PartnerInput
from ..graphql.planning_intervention_template_type import (
    PlanningInterventionTemplate,
    PlanningInterventionTemplateInput,
)
from ..graphql.planning_intervention_type import PlanningIntervention, PlanningInterventionInput
from ..graphql.service_request_line_mutation import ServiceRequestLineMutation
from ..graphql.service_request_line_query import ServiceRequestLineQuery
from ..graphql.service_request_line_type import (
    ServiceRequestLine,
    ServiceRequestLineFilterInput,
    ServiceRequestLineInput,
)
from ..graphql.service_request_mutation import ServiceRequestMutation
from ..graphql.service_request_query import ServiceRequestQuery
from ..graphql.service_request_stage_mutation import ServiceRequestStageMutation
from ..graphql.service_request_stage_query import ServiceRequestStageQuery
from ..graphql.service_request_stage_type import (
    ServiceRequestStage,
    ServiceRequestStageFilterInput,
    ServiceRequestStageInput,
)
from ..graphql.service_request_type import (
    ServiceRequest,
    ServiceRequestFilterInput,
    ServiceRequestFilterPeriodInput,
    ServiceRequestInput,
)
from ..graphql.service_request_type_mutation import ServiceRequestTypeMutation
from ..graphql.service_request_type_query import ServiceRequestTypeQuery
from ..graphql.service_request_type_type import (
    ServiceRequestType,
    ServiceRequestTypeFilterInput,
    ServiceRequestTypeInput,
)


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_service_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                ServiceRequest,
                ServiceRequestInput,
                ServiceRequestFilterInput,
                ServiceRequestQuery,
                ServiceRequestMutation,
                ServiceRequestLineQuery,
                ServiceRequestLine,
                ServiceRequestLineInput,
                ServiceRequestLineFilterInput,
                ServiceRequestLineMutation,
                ServiceRequestStageQuery,
                ServiceRequestStage,
                ServiceRequestStageInput,
                ServiceRequestStageFilterInput,
                ServiceRequestStageMutation,
                ServiceRequestTypeQuery,
                ServiceRequestType,
                ServiceRequestTypeInput,
                ServiceRequestTypeFilterInput,
                ServiceRequestTypeMutation,
                Attachment,
                AttachmentInput,
                Partner,
                PartnerInput,
                PlanningIntervention,
                PlanningInterventionInput,
                ServiceRequestFilterPeriodInput,
                PlanningInterventionTemplate,
                PlanningInterventionTemplateInput,
            ],
        )
