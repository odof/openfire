# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class DMSFile(models.Model):
    _inherit = 'dms.file'

    document_type = fields.Char(string="Document Type", compute='_compute_document_type')

    def _compute_document_type(self):
        for file in self:
            if file.res_model:
                model = self.env['ir.model'].search([('model', '=', file.res_model)])
                file.document_type = model.name
            else:
                file.document_type = False

    def action_open_document(self):
        # on va ouvrir la vue selon le modèle et l'id du document
        if not self.res_model or not self.res_id:
            raise UserError(_("Can not open view, this document is not link to a model"))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'view_mode': 'form',
            'res_id': self.res_id,
            'target': 'self',
        }
