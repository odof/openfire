# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    service_request_view = env.ref("of_equipment_service.calendar_event_view_form")
    service_request_view.unlink()
