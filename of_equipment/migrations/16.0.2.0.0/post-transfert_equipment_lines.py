# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    for event in env["calendar.event"].search([("of_type", "=", "intervention"), ("of_use_equipment", "=", True)]):
        for equipment in event.of_equipment_ids:
            # Create line in SQL to avoid recomputing duration
            now = datetime.now()
            cr.execute(
                "INSERT INTO of_calendar_event_equipment_link (event_id, equipment_id, create_date, write_date, "
                "create_uid, write_uid) VALUES (%s, %s, %s, %s, %s, %s)",
                (event.id, equipment.id, now, now, SUPERUSER_ID, SUPERUSER_ID),
            )
