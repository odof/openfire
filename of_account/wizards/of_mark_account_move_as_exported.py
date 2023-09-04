# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFMarkAccountMoveAsExported(models.TransientModel):
    _name = 'of.mark.account.move.as.exported'

    def action_button_validate(self):
        active_ids = self._context.get('active_ids')
        move_object = self.env['account.move']
        return move_object.browse(active_ids).write({'of_exported': True})
