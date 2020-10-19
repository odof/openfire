# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_specific_title = fields.Char(string=u"Titre spécifique", size=45)
    of_specific_date = fields.Date(string=u"Date spécifique")
