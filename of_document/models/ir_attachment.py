# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, values):
        res = super(IrAttachment, self).create(values)
        if res.res_model and not res.res_field:
            default_settings = self.env.ref('of_document.default_settings').sudo()
            data_ids = default_settings.of_subdirectory_ids.mapped('data_ids')
            dms_dir_obj = self.env['muk_dms.directory']
            dms_file_obj = self.env['muk_dms.file']

            # Automatically create DMS file if partner related attachment
            record = self.env[res.res_model].browse(res.res_id)
            partner, categ = dms_file_obj.of_get_object_partner_and_category(record)
            if not partner:
                return res

            partner_dir = dms_dir_obj.sudo().of_get_partner_directory(partner)

            object_dir = False
            if categ in data_ids:
                try:
                    object_dir = dms_dir_obj.of_get_object_directory(partner_dir, categ)
                except Exception:
                    pass

            # Create DMS file
            dms_file_obj.sudo().create({
                'name': res.name,
                'directory': object_dir.id if object_dir else partner_dir.id,
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
            dms_dirs.filtered(lambda directory: not directory.files and not directory.child_directories).unlink()

        return res
