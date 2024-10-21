# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    events_with_requests = env["calendar.event"].search(
        [("of_type", "=", "intervention"), ("of_request_id", "!=", False)]
    )
    for event in events_with_requests.filtered("of_use_equipment"):
        for equipment_link in event.of_linked_equipment_ids:
            # Before this version, it was not possible to have multiple equipment links for the same equipment.
            # So we can safely assume that the equipment link is unique and we can directly update the `link_id` field
            # of the first equipment line we find.
            event.of_request_id.equipment_intervention_ids.filtered(
                lambda e: e.equipment_id == equipment_link.equipment_id and e.event_id == event
            ).event_link_id = equipment_link.id
