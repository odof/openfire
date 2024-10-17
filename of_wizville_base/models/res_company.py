# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_wizville_code = fields.Char(string='Shopid Wizville')
