# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Add display config mode on all method lines"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    methods_to_update = env['account.payment.method.line'].search([])
    methods_to_update.write({'of_display_config': '{payment_amount} payé par {payment_mode} le {date}'})
