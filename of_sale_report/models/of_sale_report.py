# -*- coding: utf-8 -*-

from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_date_de_pose = fields.Date(u'Date de pose prévisionelle')
