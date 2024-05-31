# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os

from odoo import SUPERUSER_ID, api


def load_version(cr, registry):
    version_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '.openfire-version')
    if os.path.exists(version_file_path):
        with open(version_file_path, 'r') as version_file:
            version = version_file.read().strip()
    else:
        version = '!?'

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].set_param('openfire.version', version)
