# -*- coding: utf-8 -*-

from odoo import models, api

class OfWizardExport(models.TransientModel):
    _name = "of.zz.wizard.export"

    @api.multi
    def of_action_mass_edit_export(self):
        active_ids = self._context.get('active_ids')
        move_object = self.env['account.move']
        move = move_object.browse(active_ids).write({'of_export': True})
        return move
