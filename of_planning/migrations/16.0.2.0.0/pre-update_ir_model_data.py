# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _handle_planning_task_model_data(cr, env):
    cr.execute("SELECT * FROM of_planning_task WHERE name IN ('SAV', 'Maintenance')")
    tasks_data = cr.dictfetchall()
    tasks_mapping = {
        "SAV": "of_planning_task_aftersale_services",
        "Maintenance": "of_planning_task_maintenance",
    }
    for task in tasks_data:
        task_name = task["name"]
        task_data = env["ir.model.data"].search(
            [
                ("module", "=", "of_planning"),
                ("model", "=", "of.planning.task"),
                ("name", "=", tasks_mapping[task_name]),
            ]
        )
        if not task_data:
            cr.execute(
                "INSERT INTO ir_model_data (module, name, model, res_id, noupdate) "
                "VALUES ('of_planning', %s, 'of.planning.task', %s, true)",
                (tasks_mapping[task_name], task["id"]),
            )


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _handle_planning_task_model_data(cr, env)
