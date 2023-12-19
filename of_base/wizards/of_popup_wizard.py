# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfPopupWizard(models.TransientModel):
    """API fonction permettant d'afficher un message dans une fenêtre au cours de l'exécution d'une fonction"""

    _name = 'of.popup.wizard'

    message = fields.Text()

    # Usage : return self.env['of.popup.wizard'].popup_return(message[, title])
    @api.model
    def popup_return(self, message, title="Information"):
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'of.popup.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('of_base.of_popup_wizard_view').id,
            'target': 'new',
            'context': {'default_message': message},
        }
