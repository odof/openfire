# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_discount_per_so_line = fields.Selection(
        selection_add=[
            (0, 'No discount on sales order lines or invoice lines, global discount only'),
            (1, 'Allow discounts on sales order lines and invoice lines'),
        ],
    )
