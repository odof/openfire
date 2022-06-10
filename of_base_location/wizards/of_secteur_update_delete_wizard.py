# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class OFSecteurUpdateDeleteWizard(models.TransientModel):
    _name = "of.secteur.update.delete.wizard"

    @api.multi
    def button_validate(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        if context.get('update_and_delete'):
            return self.do_update_and_delete(active_ids)
        return self.do_update(active_ids)

    @api.multi
    def do_update(self, active_ids):
        for record in self.env['of.secteur'].browse(active_ids):
            record.action_update()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def do_update_and_delete(self, active_ids):
        for record in self.env['of.secteur'].browse(active_ids):
            record.action_update_delete()
        return {'type': 'ir.actions.act_window_close'}
