# -*- coding: utf-8 -*-

from odoo import fields, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    location_id = fields.Many2one(domain="[]")
