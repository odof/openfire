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
            partner, categ = self.env['muk_dms.file'].of_get_object_partner_and_category(record)
            if not partner:
                return res

            partner_dir = self.env['muk_dms.directory'].sudo().of_get_partner_directory(partner)

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
