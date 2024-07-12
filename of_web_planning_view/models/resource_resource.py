# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict
from random import randint

from odoo import fields, models

from odoo.addons.resource.models.resource import Intervals


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _default_color(self):
        return randint(1, 11)  # nosec

    color = fields.Integer(default=_default_color)
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=False,
    )

    def _get_resource_work_intervals(self, start, stop):
        """Get the work intervals of the resources within the given period.

        Inspired by the method _get_valid_work_intervals of the `resource.resource` model.

        Args:
            start (datetime): The start date of the period.
            stop (datetime): The stop date of the period.

        Returns:
            dict: The work intervals of the resources within the given period.
        """
        assert start.tzinfo and stop.tzinfo
        resources = self.env['resource.resource'].with_context(active_test=False).search([('id', 'in', self.ids)])
        resource_work_intervals = defaultdict(Intervals)
        calendar_resources = defaultdict(lambda: self.env['resource.resource'])

        resource_calendar_validity_intervals = self.sudo()._get_calendars_validity_within_period(start, stop)

        for resource in self:
            for calendar in resource_calendar_validity_intervals[resource.id]:
                calendar_resources[calendar] |= resource
        for calendar, resources in calendar_resources.items():
            work_intervals_batch = calendar._work_intervals_batch(start, stop, resources=resources)
            for resource in resources:
                resource_work_intervals[resource.id] |= (
                    work_intervals_batch[resource.id] & resource_calendar_validity_intervals[resource.id][calendar]
                )

        return resource_work_intervals
