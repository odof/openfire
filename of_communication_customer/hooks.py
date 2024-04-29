# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _delete_server_action_publish_all(env):
    """
    Remove the 'Publish' server action if it exists.
    """
    server_action = env.ref('of_communication_base.of_communication_action_publish_all', raise_if_not_found=False)
    if server_action:
        server_action.unlink()


def post_init_hook(cr, registry):
    """
    Hook executed after module installation.
    Removes the 'Publish' server action.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _delete_server_action_publish_all(env)
