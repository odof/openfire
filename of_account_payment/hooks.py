# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _set_of_payment_mode(env):
    env["of.payment.mode"].action_update_mode_payment()


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_of_payment_mode(env)
