# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    of_section_name = fields.Char(string="Section name")
    of_node_id = fields.Integer(string="Node ID")
    of_parent_node_id = fields.Integer(string="Parent Node ID")
    of_position_node = fields.Integer(string="Node's Position")
    of_level = fields.Integer(string="Level")
    of_show = fields.Boolean(string="Show line", default=True)
