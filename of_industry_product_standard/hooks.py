# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry, vals=None):
    """Unarchive the non active view"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("of_sale_product_standard.product_template_view_form").active = True
