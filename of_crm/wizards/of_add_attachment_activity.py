# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields


class OFAddAttachmentActivity(models.TransientModel):
    _name = 'of.add.attachment.activity'
    _description = 'Add an attachment to the Sale linked to an activity'

    order_id = fields.Many2one(comodel_name='sale.order', string='Order')
    lead_id = fields.Many2one(comodel_name='crm.lead', string='Lead')
    activity_id = fields.Many2one(comodel_name='of.crm.activity', string='Activity')
    activity_file = fields.Binary(comodel_name='ir.attachment', attachment=True)
    activity_filename = fields.Char(string='Filename')

    @api.multi
    def action_validate(self):
        self.ensure_one()
        if self.order_id:
            res_model = 'sale.order'
            res_id = self.order_id.id
        else:
            res_model = 'crm.lead'
            res_id = self.lead_id.id
        attachment = self.env['ir.attachment'].create({
            'name': self.activity_filename,
            'datas_fname': self.activity_filename,
            'res_model': res_model,
            'res_id': res_id,
            'type': 'binary',
            'datas': self.activity_file,
        })
        self.activity_id.uploaded_attachment_id = attachment.id
        # Close and reload the form to refresh the Attachments only from the SaleOrder Form view
        if self._context.get('close_and_reload'):
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}
