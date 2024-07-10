# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfPopupWizard(models.TransientModel):
    """Transient model to display a popup message."""

    _name = 'of.popup.wizard'
    _description = "Popup Wizard"

    message = fields.Text()
    message_html = fields.Html()

    @api.model
    def popup_return(self, message='', message_html='', title="Information"):
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'of.popup.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('of_base.of_popup_wizard_view').id,
            'target': 'new',
            'context': {'default_message': message, 'default_message_html': message_html},
        }
