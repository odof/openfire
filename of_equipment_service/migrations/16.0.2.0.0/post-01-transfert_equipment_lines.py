# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    for service_request in env["of.service.request"].search([("use_equipment", "=", True)]):
        for equipment in service_request.equipment_ids:
            env["of.service.request.equipment.link"].with_context(of_ignore_event_state=True).create(
                {
                    "service_request_id": service_request.id,
                    "equipment_id": equipment.id,
                }
            )
