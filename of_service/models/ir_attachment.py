# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    of_intervention_report = fields.Boolean(string="Intervention sheet")

    @api.model_create_multi
    def create(self, vals_list):
        if self._context.get('intervention_sheet'):
            for val in vals_list:
                val['of_intervention_report'] = True
        attachments = super().create(vals_list)
        for _attachment, vals in zip(attachments, vals_list):
            if (
                self._context.get('of_copy_to_di')
                and vals.get('res_model') == 'calendar.event'
                and vals.get('res_id')
                and isinstance(vals['res_id'], int)
            ):
                event = self.env['calendar.event'].browse(vals['res_id'])
                if event.of_request_id:
                    new_vals = vals.copy()
                    new_vals['res_model'] = 'of.service.request'
                    new_vals['res_id'] = event.of_request_id.id
                    self.env['ir.attachment'].create(new_vals)
        return attachments
