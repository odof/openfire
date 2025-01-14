# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFEquipment(models.Model):
    _inherit = "of.equipment"

    @api.model
    def _prepare_technical_attributes(self):
        return []
