# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    group_discount_on_invoice_line = fields.Boolean(
        string="(OF) Remise", implied_group='of_sale_discount.of_group_discount_on_invoice_line',
        group='account.group_account_invoice',)
