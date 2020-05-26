# -*- coding: utf-8 -*-

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, values):
        res = super(IrAttachment, self).create(values)
        # Automatically create DMS file if partner related attachment
        main_dir = self.env.ref('of_document.main_partner_directory')
        if res.res_model == 'res.partner':
            partner = self.env['res.partner'].browse(res.res_id)
            # Check existence of partner directory
            partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', partner.id)])
            if not partner_dir:
                # Create customer directory
                partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                    'parent_directory': main_dir.id,
                                                                    'partner_id': partner.id})
            self.env['muk_dms.file'].create({'name': res.name,
                                             'directory': partner_dir.id,
                                             'of_file_type': 'related',
                                             'of_related_model': 'res.partner',
                                             'of_related_id': partner.id,
                                             'of_attachment_id': res.id})
        elif res.res_model in ('sale.order', 'purchase.order', 'account.invoice', 'stock.picking', 'crm.lead',
                               'project.issue', 'of.service'):
            record = self.env[res.res_model].browse(res.res_id)
            if record.partner_id:
                # Check existence of partner directory
                partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', record.partner_id.id)])
                if not partner_dir:
                    # Create customer directory
                    partner_dir = self.env['muk_dms.directory'].create({'name': record.partner_id.name,
                                                                        'parent_directory': main_dir.id,
                                                                        'partner_id': record.partner_id.id})
                self.env['muk_dms.file'].create({'name': res.name,
                                                 'directory': partner_dir.id,
                                                 'of_file_type': 'related',
                                                 'of_related_model': res.res_model,
                                                 'of_related_id': record.partner_id.id,
                                                 'of_attachment_id': res.id})
        return res

    @api.multi
    def unlink(self):
        # Automatically delete DMS file if partner related attachment
        for attachment in self:
            dms_file = self.env['muk_dms.file'].search([('of_attachment_id', '=', attachment.id)])
            if dms_file:
                dms_dir = dms_file.directory
                dms_file.unlink()
                # Delete DMS directory if no file left
                if not dms_dir.files:
                    dms_dir.unlink()
        return super(IrAttachment, self).unlink()
