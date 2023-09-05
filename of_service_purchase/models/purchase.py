# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    of_service_id = fields.Many2one(
        comodel_name='of.service', string="DI d'origine", compute='_compute_of_service_id')
    of_date_next = fields.Date(string=u"Date d'intervention", readonly=True)
    of_date_end = fields.Date(string=u"Date de fin d'intervention", readonly=True)

    @api.depends('order_line.of_service_line_id')
    def _compute_of_service_id(self):
        for record in self:
            services = record.order_line.mapped('of_service_line_id').mapped('service_id')
            record.of_service_id = services and services[0]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_service_line_id = fields.Many2one(comodel_name='of.service.line', string=u"Ligne de DI")
