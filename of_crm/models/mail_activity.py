# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = "mail.activity"

    delay_count = fields.Integer(related="activity_type_id.delay_count")
    delay_unit = fields.Selection(related="activity_type_id.delay_unit")
    delay_from = fields.Selection(related="activity_type_id.delay_from")
    date_deadline = fields.Date(compute="_compute_date_deadline", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        new_values = []
        activities_package = False

        for vals in vals_list:
            if activity_type_id := vals.get("activity_type_id", False):
                activity_type = self.env["mail.activity.type"].browse(activity_type_id)

                # check if the category is activities_lot, if so, we create the associated activities instead
                if activity_type.category == "activities_lot":
                    activities_package = True
                    base_date = fields.Date.context_today(self)
                    previous_activity_date = base_date
                    for at in activity_type.of_activities_type:
                        value = vals.copy()
                        value["activity_type_id"] = at.id
                        value["summary"] = at.summary
                        value["note"] = at.default_note
                        value["delay_count"] = at.delay_count
                        value["delay_unit"] = at.delay_unit
                        value["delay_from"] = at.delay_from

                        # Déterminer la date de base
                        if at.delay_from == "previous_activity":
                            base_date = previous_activity_date

                        # Calculer la date_deadline
                        value["date_deadline"] = base_date + relativedelta(**{at.delay_unit: at.delay_count})
                        previous_activity_date = value["date_deadline"]

                        if at.default_user_id:
                            value["user_id"] = at.default_user_id.id
                        new_values.append(value)
                else:
                    new_values.append(vals)

        activities = super().create(new_values)

        # When creating a package of activities from the form view, an error is raised because Odoo is waiting
        # for a single record and not a recordset. We therefore return the first record of the recordset.
        return activities[0] if activities_package else activities
