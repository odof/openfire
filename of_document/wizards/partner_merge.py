# -*- coding: utf-8 -*-

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
                    src_partner_dir.files.write({'directory': top_partner_dir.id,
                                                 'of_attachment_partner_id': dst_partner.id})

                    # Delete src partner DMS directory
                    src_partner_dir.unlink()
                else:
                    dms_file_obj.search([('of_attachment_partner_id', '=', src_partner.id)])\
                        .write({'directory': top_partner_dir.id, 'of_attachment_partner_id': dst_partner.id})

                dms_file_obj.\
                    search([('of_related_model', '=', 'res.partner'), ('of_related_id', '=', src_partner.id)]).\
                    write({'of_related_id': dst_partner.id})

        super(MergePartnerAutomatic, self)._update_foreign_keys(src_partners, dst_partner)
