# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFPlanningTour(models.Model):
    _inherit = "of.planning.tour"

    def _get_initial_available_slots_recursive(self, tour, available_slots, leave):
        """
        Recursively updates the initial available slots based on the given tour employee leave.

        Args:
            tour (Tour): The tour object.
            available_slots (list): The list of available slots.
            leave (HRLeave): HR Leave object.

        Returns:
            list: The list of updated available slots.
        """
        if available_slots:
            res = []
            slot = available_slots[0]
            if slot["start"] > leave.date_to or slot["stop"] < leave.date_from:
                res = [slot]
            elif leave.date_from <= slot["start"] and leave.date_to >= slot["stop"]:
                # This tour line is superpozed with the entire leave slot, so we delete it
                pass
            elif leave.date_from <= slot["start"]:
                # This tour line is superpozed with the start of the leave slot
                slot.start = leave.date_to
                res = [slot]
            elif leave.date_from > slot["start"] and leave.date_to < slot["stop"]:
                # This tour line is inside of the available slot, a split is needed
                available_slots.insert(
                    1,
                    {"start": leave.date_to, "stop": slot["stop"]},
                )
                slot.stop = leave.date_from
                res = [slot]
            elif leave.date_to >= slot["stop"]:
                # This tour line is superpozed with the end of the leave slot
                slot.stop = leave.date_from
                res = [slot]

            recursive = self._get_initial_available_slots_recursive(tour, available_slots[1:], leave)
            return res + recursive
        else:
            return []

    def _get_initial_available_slots(self, tour):
        available_slots = super()._get_initial_available_slots(tour)
        leave_obj = self.env["hr.leave"]
        leaves = leave_obj.search(
            [
                ("employee_id", "=", tour.employee_id.id),
                ("state", "=", "validate"),
                ("request_date_from", "<=", tour.date),
                ("request_date_to", ">=", tour.date),
            ]
        )
        for leave in leaves:
            available_slots = self._get_initial_available_slots_recursive(tour, available_slots, leave)

        return available_slots
