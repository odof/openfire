# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model_create_multi
    def create(self, vals_list):
        res = []
        activities_package = False
        for vals in vals_list:
            if activity_type_id := vals.get('activity_type_id', False):
                activity_type = self.env['mail.activity.type'].browse(activity_type_id)
                # check if the category is activities_lot, if so, we create the associated activities instead
                if activity_type.category == 'activities_lot':
                    activities_package = True
                    for at in activity_type.of_activities_type:
                        value = vals.copy()
                        value['activity_type_id'] = at.id
                        res.append(value)
                else:
                    res.append(vals)
        activities = super().create(res)
        # When creating a package of activities from the form view, an error is raised because Odoo is waiting
        # for a single record and not a recordset. We therefore return the first record of the recordset.
        return activities[0] if activities_package else activities
