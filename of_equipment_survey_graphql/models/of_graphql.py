# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.equipment_intervention_report_template_type import (
    EquipmentInterventionReportTemplate,
    EquipmentInterventionReportTemplateInput,
)
from ..graphql.planning_intervention_equipment_link_type import (
    PlanningInterventionEquipmentLink,
    PlanningInterventionEquipmentLinkInput,
)


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_equipment_survey_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                EquipmentInterventionReportTemplate,
                EquipmentInterventionReportTemplateInput,
                PlanningInterventionEquipmentLink,
                PlanningInterventionEquipmentLinkInput,
            ],
        )
