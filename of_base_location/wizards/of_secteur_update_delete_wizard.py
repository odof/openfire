# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class OFSectorUpdateDeleteWizard(models.TransientModel):
    _name = 'of.sector.update.delete.wizard'

    def action_button_validate(self):
        context = self._context.copy()
        active_ids = context.get('active_ids', [])
        if context.get('update_and_delete'):
            return self.do_update_and_delete(active_ids)
        return self.do_update(active_ids)

    def do_update(self, active_ids):
        for record in self.env['of.sector'].browse(active_ids):
            record.action_update()
        return {'type': 'ir.actions.act_window_close'}

    def do_update_and_delete(self, active_ids):
        for record in self.env['of.sector'].browse(active_ids):
            record.action_update_delete()
        return {'type': 'ir.actions.act_window_close'}
