# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _recompute_tours(cr, env):
    """Re-compute all coming tours for existing employees."""
    env["hr.employee"].search([])._recompute_tours()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _recompute_tours(cr, env)
