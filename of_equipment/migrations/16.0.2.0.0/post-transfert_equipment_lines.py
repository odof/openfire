# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    for event in env["calendar.event"].search([("of_type", "=", "intervention"), ("of_use_equipment", "=", True)]):
        for equipment in event.of_equipment_ids:
            env["of.calendar.event.equipment.link"].with_context(of_ignore_event_state=True).create(
                {
                    "event_id": event.id,
                    "equipment_id": equipment.id,
                }
            )
