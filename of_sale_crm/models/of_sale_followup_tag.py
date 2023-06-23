# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleFollowupTag(models.Model):
    _name = 'of.sale.followup.tag'
    _description = "Order tracking label"

    sequence = fields.Integer(required=True, default=1)
    name = fields.Char(required=True)
    color = fields.Integer()

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'This tag name already exists'),
    ]
