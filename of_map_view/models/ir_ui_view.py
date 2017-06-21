# -*- coding: utf-8 -*-

from odoo import models, fields

MAP_VIEW = ('map', 'Map')

class IrUIView(models.Model):

    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[MAP_VIEW])
