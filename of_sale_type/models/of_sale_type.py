# -*- coding: utf-8 -*-

from odoo import fields, models


class OfSaleType(models.Model):
    _name = 'of.sale.type'
    _description = "Sale Order Type"
    _order = 'sequence, name'

    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Name", required=True)
