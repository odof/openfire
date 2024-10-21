# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    for service_request in env["of.service.request"].search([("use_equipment", "=", True)]):
        for equipment in service_request.equipment_ids:
            # Create line in SQL to avoid recomputing on service request
            now = datetime.now()
            cr.execute(
                "INSERT INTO of_service_request_equipment_link (service_request_id, equipment_id, "
                "create_date, write_date, create_uid, write_uid) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    service_request.id,
                    equipment.id,
                    now,
                    now,
                    SUPERUSER_ID,
                    SUPERUSER_ID,
                ),
            )
