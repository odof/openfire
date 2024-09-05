# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IRActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('planning', "Planning")], ondelete={'planning': 'cascade'})


class IRActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def action_add_view_mode_planning(self):
        for action in self:
            view_modes = action.view_mode.split(',')
            if 'planning' not in view_modes:
                view_modes.append('planning')
                action.view_mode = ','.join(view_modes)
