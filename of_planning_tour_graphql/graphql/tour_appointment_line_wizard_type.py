# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.employee_type import Employee


class DayPeriod(graphene.Enum):
    BOTH = "both"
    MORNING = "morning"
    AFTERNOON = "afternoon"


class TourAppointmentLineWizard(OdooObjectType):
    _name = "TourAppointmentLineWizard"
    _type = "types"

    id = graphene.Int(required=True)
    employee_id = graphene.Field(Employee, name="employee", required=True)
    date = graphene.Date(required=True)
    previous_duration = graphene.Float(required=True)
    next_duration = graphene.Float(required=True)
    previous_distance = graphene.Float(required=True)
    next_distance = graphene.Float(required=True)
    time_slot = graphene.String(required=True)
    start = graphene.DateTime(required=True)
