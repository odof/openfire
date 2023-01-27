# -*- coding: utf-8 -*-

from odoo import api, fields, models

from datetime import datetime
import pytz


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_requested_week = fields.Char(string=u"Semaine demandée", compute='_compute_of_requested_week', store=True)

    @api.depends('requested_date')
    def _compute_of_requested_week(self):
        for order in self:
            if order.requested_date:
                requested_year = fields.Date.from_string(order.requested_date).year
                requested_date = datetime.strptime(order.requested_date, "%Y-%m-%d %H:%M:%S")
                requested_date_utc = pytz.utc.localize(requested_date)
                tz = pytz.timezone(self.env.user.tz or "Europe/Paris")
                requested_date_tz = requested_date_utc.astimezone(tz)
                requested_week = requested_date_tz.date().isocalendar()[1]
                order.of_requested_week = "%s - S%02d" % (requested_year, requested_week)
            else:
                order.of_requested_week = ""

    def pdf_requested_week(self):
        # Pour éviter de créer un module intermédiaire entre of_sale_external et of_sale_order_dates,
        # on teste la présence d'un champ créé dans of_sale_external
        if 'of_report_template_id' in self.env['sale.order']._fields and self.of_report_template_id:
            return self.of_report_template_id.pdf_requested_week
        else:
            return self.env['ir.values'].get_default('sale.config.settings', 'pdf_requested_week')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_order_requested_week = fields.Char(
        string=u"Semaine demandée", related='order_id.of_requested_week', readonly=True, store=True)
