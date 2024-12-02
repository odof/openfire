# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFEquipmentTag(models.Model):
    _name = "of.equipment.tag"
    _description = "Étiquette d'équipement"
    _order = "sequence"

    name = fields.Char(string="Libellé", required=True, translate=True)
    sequence = fields.Integer(help="Used to order tags. Lower is better.", default=1)
    active = fields.Boolean(default=True, help="Hides the label without deleting it.")
    color = fields.Integer(string="Color index")
