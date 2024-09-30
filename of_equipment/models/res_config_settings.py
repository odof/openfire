# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_equipment_auto_create = fields.Boolean(
        string="(OF) Automatic creation of equipment",
        related="company_id.of_equipment_auto_create",
        help="Automatically create the equipment on picking confirmation if a serial number is assigned.",
        readonly=False,
    )

    @api.onchange("group_stock_production_lot")
    def _onchange_group_stock_production_lot(self):
        if not self.group_stock_production_lot:
            self.of_equipment_auto_create = False
        super()._onchange_group_stock_production_lot()
