# -*- coding: utf-8 -*-

from odoo import fields, models


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    sale_comp_id = fields.Many2one('sale.order.line.comp', string='Sale Order Line Component')
