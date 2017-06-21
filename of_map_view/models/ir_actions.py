# -*- coding: utf-8 -*-

from odoo import models, fields

MAP_VIEW = ('map', 'Map')

class IrActionsActWindowView(models.Model):

    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[MAP_VIEW])
