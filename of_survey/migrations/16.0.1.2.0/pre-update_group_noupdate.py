# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _update_group_noupdate(cr, env):
    """Updates the noupdate for group and module category."""
    datas = env["ir.model.data"].search(
        [("model", "in", ["res.groups", "ir.module.category"]), ("module", "=", "of_survey")]
    )
    datas.write({"noupdate": False})


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_group_noupdate(cr, env)
