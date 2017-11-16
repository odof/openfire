# -*- encoding: utf-8 -*-

from odoo import api, models, fields

class OFResUsers(models.Model):
    _inherit = 'res.users'

    int_test = fields.Integer("entier test")
