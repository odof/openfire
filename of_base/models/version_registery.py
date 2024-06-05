# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from .. import version_loader


class VersionRegistry(models.AbstractModel):
    _name = 'version.registry'
    _description = 'Version Registry'

    @api.model
    def _register_hook(self):
        version_loader.load_version(self.env.cr, self.env.registry)
        return super()._register_hook()
