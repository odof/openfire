# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

import pytz

from odoo import api, fields, models

from odoo.addons.resource.models.resource import float_to_time


class OFPlanningTour(models.Model):
    _inherit = "of.planning.tour"

    employee_web_resource_calendar_id = fields.Many2one(
        related="employee_id.of_web_resource_calendar_id", readonly=True
    )
    available_slot_ids = fields.One2many(domain=[("type", "=", "regular")])
    web_available_slot_ids = fields.One2many(
        comodel_name="of.planning.available.slot",
        inverse_name="tour_id",
        string="Web Available Slots",
        copy=False,
        domain=[("type", "=", "web")],
    )

    @api.model_create_multi
    def create(self, vals_list):
        tours = super().create(vals_list)

        # Initialize web available slots
        for tour in tours:
            web_available_slots = self._get_initial_web_available_slots(tour)
            self._update_web_available_slot(tour, web_available_slots)

        return tours

    def _get_initial_web_available_slots(self, tour):
        """
        Creation of the initial web available slots for this tour.
        If employee doesn't have a resource calendar for web there is no available slots returned.

        Args:
            tour (Tour): The tour object for which to create the available slots.

        Returns:
            list: A list of dictionaries representing the web available slots. Each dictionary contains
                    the 'start' and 'stop' datetime values for a slot.
        """
        web_available_slots = []

        if tour.employee_id.of_web_resource_calendar_id and tour.date >= fields.Date.today():
            calendar_tz = pytz.timezone(tour.employee_id.of_web_resource_calendar_id.tz)

            for attendance in tour.mapped("employee_id.of_web_resource_calendar_id.attendance_ids").filtered(
                lambda a: not a.display_type
                and a.dayofweek == str(tour.date.weekday())
                and (not a.week_type or a.week_type == tour.week_type)
            ):
                start_time = float_to_time(attendance.hour_from)
                stop_time = float_to_time(attendance.hour_to)
                start = calendar_tz.localize(datetime.combine(tour.date, start_time))
                stop = calendar_tz.localize(datetime.combine(tour.date, stop_time))

                web_available_slots.append(
                    {
                        "start": start.astimezone(pytz.utc).replace(tzinfo=None),
                        "stop": stop.astimezone(pytz.utc).replace(tzinfo=None),
                    }
                )
        return web_available_slots

    @api.model
    def _update_available_slot(self, tour, available_slots):
        """
        We update the existing available slots with the new info. If there is too much slots, we archive them.
        If there is not enough, we create them.

        Overriding `of_planning_tour/models/of_planning_tour.py` to add the new type domain `regular`
        """
        available_slot_obj = self.env["of.planning.available.slot"]
        tour_available_slots = available_slot_obj.with_context(active_test=False).search(
            [("tour_id", "=", tour.id), ("type", "=", "regular")]
        )
        for slot_dict in available_slots:
            slot_dict.update({"active": True, "tour_id": tour.id})
            if tour_available_slots:
                tour_available_slots[0].write(slot_dict)
                tour_available_slots = tour_available_slots - tour_available_slots[0]
            else:
                available_slot_obj.create(slot_dict)
        if tour_available_slots:
            tour_available_slots.write({"active": False})

    @api.model
    def _update_web_available_slot(self, tour, web_available_slots):
        """
        We update the existing available slots with the new info. If there is too much slots, we archive them.
        If there is not enough, we create them.
        """
        available_slot_obj = self.env["of.planning.available.slot"]
        tour_web_available_slots = available_slot_obj.with_context(active_test=False).search(
            [("tour_id", "=", tour.id), ("type", "=", "web")]
        )
        for slot_dict in web_available_slots:
            slot_dict.update({"active": True, "tour_id": tour.id, "type": "web"})
            if tour_web_available_slots:
                tour_web_available_slots[0].write(slot_dict)
                tour_web_available_slots = tour_web_available_slots - tour_web_available_slots[0]
            else:
                available_slot_obj.create(slot_dict)
        if tour_web_available_slots:
            tour_web_available_slots.write({"active": False})

    def _reorganize_available_slot(self):
        super()._reorganize_available_slot()

        for tour in self:
            web_available_slots = self._get_initial_web_available_slots(tour)
            web_available_slots = self._populate_available_slots(tour, web_available_slots)
            web_available_slots = self._delete_available_slot_too_small(web_available_slots)
            self._update_web_available_slot(tour, web_available_slots)
