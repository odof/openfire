# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_datastore_purchase_id = fields.Integer(string="ID commande base fille", copy=False)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_datastore_line_id = fields.Integer(string="ID base fille", copy=False)

