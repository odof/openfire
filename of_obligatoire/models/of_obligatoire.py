# -*- coding: utf-8 -*-

from odoo import api, models, SUPERUSER_ID
from odoo.exceptions import UserError

class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    # Permet d'empêcher l'installation, la désinstallation, la mise à jour de module par les utilisateurs autre que admin.
    @api.multi
    def write(self, vals):
        if self._uid != SUPERUSER_ID and 'state' in vals:
            if vals['state'] == 'to install':
                raise UserError(u'Vous ne pouvez pas installer de module. Veuillez contacter votre administrateur système.')
            if vals['state'] == 'to remove':
                raise UserError(u'Vous ne pouvez pas désinstaller de module. Veuillez contacter votre administrateur système.')
            if vals['state'] == 'to upgrade':
                raise UserError(u'Vous ne pouvez pas mettre à jour de module. Veuillez contacter votre administrateur système.')
        return super(IrModuleModule, self).write(vals)
