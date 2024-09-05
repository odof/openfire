# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IRActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('map', "Map")], ondelete={'map': 'cascade'})


class IRActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def action_add_view_mode_map(self):
        for action in self:
            view_modes = action.view_mode.split(',')
            if 'map' not in view_modes:
                view_modes.append('map')
                action.view_mode = ','.join(view_modes)


class IRActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def action_add_binding_view_type_map(self):
        for action in self:
            view_modes = action.binding_view_types.split(',')
            if 'map' not in view_modes:
                view_modes.append('map')
                action.binding_view_types = ','.join(view_modes)


class IRActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    def action_add_binding_view_type_map(self):
        for action in self:
            view_modes = action.binding_view_types.split(',')
            if 'map' not in view_modes:
                view_modes.append('map')
                action.binding_view_types = ','.join(view_modes)
