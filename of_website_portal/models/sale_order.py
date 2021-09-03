# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_show_price_subtotal = fields.Boolean(group='base.group_portal,base.group_user')
    group_show_price_total = fields.Boolean(group='base.group_portal,base.group_user')
