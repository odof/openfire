# -*- coding: utf-8 -*-

from odoo import api, fields, models

from datetime import datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_requested_week = fields.Char(string=u"Semaine demandée", compute='_compute_of_requested_week', store=True)

    @api.depends('requested_date')
    def _compute_of_requested_week(self):
        for order in self:
            if order.requested_date:
                requested_year = fields.Date.from_string(order.requested_date).year
                requested_week = datetime.strptime(order.requested_date, "%Y-%m-%d %H:%M:%S").date().isocalendar()[1]
                order.of_requested_week = "%s - S%02d" % (requested_year, requested_week)
            else:
                order.of_requested_week = ""


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_order_requested_week = fields.Char(
        string=u"Semaine demandée", related='order_id.of_requested_week', readonly=True, store=True)
