# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_price_printing = fields.Selection(selection_add=[('without_any_price', u'Sans prix')])
