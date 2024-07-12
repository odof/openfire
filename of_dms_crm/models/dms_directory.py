# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class DMSDirectory(models.Model):
    _inherit = "dms.directory"

    def _get_translated_name(self):
        res = super()._get_translated_name()
        if res == "Leads":
            return "Opportunités"
        return res
