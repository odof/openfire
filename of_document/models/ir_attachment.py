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
    def write(self, vals):
        result = super(IrAttachment, self).write(vals)
        if 'res_model' in vals or 'res_id' in vals:
            for rec in self:
                default_settings = self.env.ref('of_document.default_settings').sudo()
                data_ids = default_settings.of_subdirectory_ids.mapped('data_ids')
                dms_dir_obj = self.env['muk_dms.directory']
                dms_file_obj = self.env['muk_dms.file']

                # Test if attachment is already linked to a DMS file
                dms_file = dms_file_obj.sudo().search([('of_attachment_id', '=', rec.id)])

                if dms_file:
                    # Delete or move DMS file to corresponding directory if needed
                    record = self.env[rec.res_model].browse(rec.res_id)
                    partner, categ = dms_file_obj.of_get_object_partner_and_category(record)
                    if not partner:
                        # Delete DMS file
                        dms_file.of_file_type = 'normal'
                        dms_file.unlink()
                        continue

                    partner_dir = dms_dir_obj.sudo().of_get_partner_directory(partner)

                    object_dir = False
                    if categ in data_ids:
                        try:
                            object_dir = dms_dir_obj.of_get_object_directory(partner_dir, categ)
                        except Exception:
                            pass

                    # Update DMS file
                    new_file_vals = {}

                    if rec.res_model != dms_file.of_related_model:
                        new_file_vals['of_related_model'] = rec.res_model

                    if rec.res_id != dms_file.of_related_id:
                        new_file_vals['of_related_id'] = rec.res_id

                    if object_dir:
                        if object_dir != dms_file.directory:
                            new_file_vals['directory'] = object_dir.id
                    elif partner_dir != dms_file.directory:
                        new_file_vals['directory'] = partner_dir.id

                    if partner != dms_file.of_attachment_partner_id:
                        new_file_vals['of_attachment_partner_id'] = partner.id

                    if dms_file.of_category_id != categ:
                        new_file_vals['of_category_id'] = categ.id

                    if new_file_vals:
                        dms_file.write(new_file_vals)
                else:
                    # Automatically create DMS file if partner related attachment
                    record = self.env[rec.res_model].browse(rec.res_id)
                    partner, categ = dms_file_obj.of_get_object_partner_and_category(record)
                    if not partner:
                        continue

                    partner_dir = dms_dir_obj.sudo().of_get_partner_directory(partner)

                    object_dir = False
                    if categ in data_ids:
                        try:
                            object_dir = dms_dir_obj.of_get_object_directory(partner_dir, categ)
                        except Exception:
                            pass

                    # Create DMS file
                    dms_file_obj.sudo().create({
                        'name': rec.name,
                        'directory': object_dir.id if object_dir else partner_dir.id,
                        'of_file_type': 'related',
                        'of_related_model': rec.res_model,
                        'of_related_id': rec.res_id,
                        'of_attachment_id': rec.id,
                        'of_attachment_partner_id': partner.id,
                        'size': rec.file_size,
                        'of_category_id': categ.id,
                    })

        return result

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
