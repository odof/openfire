# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class OFSaleFollowupTag(models.Model):
    _name = 'of.sale.followup.tag'
    _description = "Order tracking label"

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'This tag name already exists !'),
    ]
