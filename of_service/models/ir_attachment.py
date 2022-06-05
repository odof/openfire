# -*- encoding: utf-8 -*-

from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    of_intervention_report = fields.Boolean(string="Fiche d'intervention")

    def create(self, vals):
        if self._context.get('fiche_intervention'):
            vals['of_intervention_report'] = True
        attachment = super(IrAttachment, self).create(vals)
        if self._context.get('copy_to_di') and vals.get('res_model', '') == 'of.planning.intervention' \
                and vals.get('res_id') and isinstance(vals['res_id'], int):
            interv = self.env['of.planning.intervention'].browse(vals['res_id'])
            if interv.service_id:
                new_vals = vals.copy()
                new_vals['res_model'] = 'of.service'
                new_vals['res_id'] = interv.service_id.id
                self.env['ir.attachment'].create(new_vals)
        return attachment
