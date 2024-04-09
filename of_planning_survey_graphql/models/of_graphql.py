# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.planning_intervention_template_type import PlanningInterventionTemplate
from ..graphql.planning_intervention_type import PlanningIntervention


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_planning_survey_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [PlanningIntervention, PlanningInterventionTemplate],
        )
