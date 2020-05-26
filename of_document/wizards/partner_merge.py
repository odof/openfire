# -*- coding: utf-8 -*-

import unidecode

from odoo import api, fields, models


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    @api.model
    def _update_foreign_keys(self, src_partners, dst_partner):
        """Manage DMS before many2one fields update"""
        if self.env['muk_dms.directory'].search([('of_partner_id', 'in', src_partners.ids)]) or \
                self.env['muk_dms.file'].\
                search([('of_related_model', '=', 'res.partner'), ('of_related_id', 'in', src_partners.ids)]):
            # Check existence of top dst partner directory
            top_partner = dst_partner
            while top_partner.parent_id:
                top_partner = top_partner.parent_id
            top_partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
            if not top_partner_dir:
                # Find parent directory
                top_partner_first_char = (unidecode.unidecode(top_partner.name[0])).lower()
                if top_partner_first_char.isalpha():
                    try:
                        parent_dir = self.env.ref('of_document.' + top_partner_first_char + '_partner_directory')
                    except:
                        parent_dir = self.env.ref('of_document.other_partner_directory')
                else:
                    parent_dir = self.env.ref('of_document.other_partner_directory')

                # Create partner directory
                top_partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                        'parent_directory': parent_dir.id,
                                                                        'of_partner_id': top_partner.id})

            for src_partner in src_partners:
                src_partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', src_partner.id)])
                if src_partner_dir:
                    # Move DMS files into top dst partner DMS directory
                    self.env['muk_dms.file'].search([('directory', '=', src_partner_dir.id)]). \
                        write({'directory': top_partner_dir.id})

                    # Delete src partner DMS directory
                    src_partner_dir.unlink()

                self.env['muk_dms.file'].\
                    search([('of_related_model', '=', 'res.partner'), ('of_related_id', '=', src_partner.id)]).\
                    write({'of_related_id': dst_partner.id})

        super(MergePartnerAutomatic, self)._update_foreign_keys(src_partners, dst_partner)
