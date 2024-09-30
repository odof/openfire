# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    of_equipment_auto_create = fields.Boolean(
        string="(OF) Automatic creation of equipment",
        help="Automatically create the equipment on picking confirmation if a serial number is assigned.",
    )
