# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFImage(models.Model):
    _inherit = "of.image"

    equipment_link_id = fields.Many2one(string="Equipment", comodel_name="of.calendar.event.equipment.link")
