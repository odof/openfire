# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_sale_type_id = fields.Many2one(comodel_name='of.sale.type', string="Sale order type")
