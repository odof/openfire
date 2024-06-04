# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.configuration_query import ConfigurationQuery
from ..graphql.configuration_type import Configuration
from ..graphql.employee_query import EmployeeQuery
from ..graphql.employee_type import Employee
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
from ..graphql.user_type import User


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_mobile_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Configuration,
                User,
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
                PlanningInterventionTemplate,
                PlanningInterventionTemplateInput,
                PlanningInterventionTemplateFilterInput,
                PlanningInterventionTemplateAdditionalLine,
                PlanningInterventionTemplateAdditionalLineFilterInput,
                PlanningInterventionTemplateAdditionalLineInput,
            ],
        )
