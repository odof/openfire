from odoo import fields, models

MAP_VIEW = ('map', 'Map')


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[MAP_VIEW])
