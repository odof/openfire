# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.tour_appointment_line_wizard_query import TourAppointmentLineWizardQuery
from ..graphql.tour_appointment_line_wizard_type import TourAppointmentLineWizard


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_planning_tour_graphql_register(self, dbname):
        OdooGraphql.add(
            dbname,
            [
                TourAppointmentLineWizard,
                TourAppointmentLineWizardQuery,
            ],
        )
