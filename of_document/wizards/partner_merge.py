# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    @api.model
    def _update_foreign_keys(self, src_partners, dst_partner):
        """Manage DMS before many2one fields update"""
        dms_dir_obj = self.env['muk_dms.directory'].sudo()
        dms_file_obj = self.env['muk_dms.file'].sudo()
        if dms_dir_obj.search([('of_partner_id', 'in', src_partners.ids)]) or \
                dms_file_obj.search([('of_attachment_partner_id', 'in', src_partners.ids)]):
            top_partner_dir = dms_dir_obj.of_get_partner_directory(dst_partner)
            for src_partner in src_partners:
                src_partner_dir = dms_dir_obj.search([('of_partner_id', '=', src_partner.id)])
                if src_partner_dir:
                    # Move DMS files into top dst partner DMS directory
                    to_process = [(src_partner_dir, top_partner_dir)]
                    to_unlink = dms_dir_obj
                    while to_process:
                        src_dir, dest_dir = to_process.pop(0)
                        to_unlink += src_dir
                        src_dir.files.write({
                            'directory': dest_dir.id,
                            'of_attachment_partner_id': dst_partner.id})
                        for sub_src_dir in src_dir.child_directories:
                            if not dms_file_obj.search([('directory', 'child_of', sub_src_dir.id)], limit=1):
                                continue
                            sub_dest_dir = dest_dir.child_directories.filtered(lambda d: d.name == sub_src_dir.name)
                            if sub_dest_dir:
                                to_process.append((sub_src_dir, sub_dest_dir))
                            else:
                                sub_src_dir.parent_directory = dest_dir

                    # Delete src partner DMS directories
                    to_unlink.unlink()
                else:
                    dms_file_obj.search([('of_attachment_partner_id', '=', src_partner.id)])\
                        .write({'directory': top_partner_dir.id, 'of_attachment_partner_id': dst_partner.id})

                dms_file_obj.\
                    search([('of_related_model', '=', 'res.partner'), ('of_related_id', '=', src_partner.id)]).\
                    write({'of_related_id': dst_partner.id})

        super(MergePartnerAutomatic, self)._update_foreign_keys(src_partners, dst_partner)
