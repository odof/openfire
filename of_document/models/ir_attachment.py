# -*- coding: utf-8 -*-

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, values):
        res = super(IrAttachment, self).create(values)
        if res.res_model and not res.res_field:
            # Automatically create DMS file if partner related attachment
            record = self.env[res.res_model].browse(res.res_id)
            partner = False
            if res.res_model == 'res.partner':
                partner = record
            elif res.res_model in ('sale.order', 'purchase.order', 'account.invoice', 'stock.picking', 'crm.lead',
                                   'project.issue', 'of.service', 'of.planning.intervention'):
                if res.res_model == 'stock.picking':
                    if record.picking_type_id.code not in ('outgoing', 'incoming'):
                        return res

                partner = record.partner_id
            if not partner:
                return res

            partner_dir = self.env['muk_dms.directory'].sudo().of_get_partner_directory(partner)

            # Get corresponding category
            if res.res_model == 'account.invoice':
                if record.type in ('out_invoice', 'out_refund'):
                    categ = self.env.ref('of_document.account_invoice_out_file_category')
                else:
                    categ = self.env.ref('of_document.account_invoice_in_file_category')
            elif res.res_model == 'stock.piking':
                if record.picking_type_id.code == 'outgoing':
                    categ = self.env.ref('of_document.stock_picking_out_file_category')
                else:
                    categ = self.env.ref('of_document.stock_picking_in_file_category')
            else:
                categ = self.env.ref('of_document.' + res.res_model.replace('.', '_') + '_file_category')

            # Create DMS file
            self.env['muk_dms.file'].sudo().create({
                'name': res.name,
                'directory': partner_dir.id,
                'of_file_type': 'related',
                'of_related_model': res.res_model,
                'of_related_id': res.res_id,
                'of_attachment_id': res.id,
                'of_attachment_partner_id': partner.id,
                'size': res.file_size,
                'of_category_id': categ.id,
            })

        return res

    @api.multi
    def unlink(self):
        # Automatically delete DMS file if partner related attachment
        dms_files_to_delete = self.env['muk_dms.file'].sudo().search([('of_attachment_id', 'in', self.ids)])

        res = super(IrAttachment, self).unlink()

        if dms_files_to_delete:
            dms_dirs = dms_files_to_delete.mapped('directory')
            dms_files_to_delete.unlink()
            # Delete DMS directory if no file left
            dms_dirs.filtered(lambda directory: not directory.files).unlink()

        return res
