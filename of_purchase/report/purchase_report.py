# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    price_total = fields.Integer()
    price_average = fields.Integer()
    negociation = fields.Integer()
    price_standard = fields.Integer()
