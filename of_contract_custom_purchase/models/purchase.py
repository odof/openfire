# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_service_line_id = fields.Many2one(comodel_name='of.service.line', string=u"Ligne de DI")
