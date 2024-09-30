# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry, vals=None):
    """To manage the conflict between the two modules :
    - we had deactivate the search view of the sms module causing the problem in `of_base`
    - we disabled specific search view of our module in `of_base`
    - we re-enable the search view of the sms module in `of_base_sms`
    - and finally we activate the new specific search view of our module in `of_base_sms` that add our phone filter
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("of_base.of_res_partner_phone_filter").active = False
    env.ref("sms.res_partner_view_search").active = True  # could be deactivated by of_base `post_init_hook`
    env.ref("of_base_sms.res_partner_view_search").active = True


def uninstall_hook(cr, registry, vals=None):
    """Reset the search view of the sms module to the default one."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("of_base_sms.res_partner_view_search").active = False
    if env["ir.module.module"]._get("sms").state == "uninstalled":
        env.ref("of_base.of_res_partner_phone_filter").active = True
