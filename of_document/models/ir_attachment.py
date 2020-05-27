# -*- coding: utf-8 -*-

import unidecode

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, values):
        res = super(IrAttachment, self).create(values)
        if not res.res_field:
            # Automatically create DMS file if partner related attachment
            if res.res_model == 'res.partner':
                partner = self.env['res.partner'].browse(res.res_id)

                # Check existence of top partner directory
                top_partner = partner
                while top_partner.parent_id:
                    top_partner = top_partner.parent_id
                partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                if not partner_dir:
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
                    partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                        'parent_directory': parent_dir.id,
                                                                        'partner_id': top_partner.id})
                self.env['muk_dms.file'].create({'name': res.name,
                                                 'directory': partner_dir.id,
                                                 'of_file_type': 'related',
                                                 'of_related_model': 'res.partner',
                                                 'of_related_id': partner.id,
                                                 'of_attachment_id': res.id,
                                                 'size': res.file_size})
            elif res.res_model in ('sale.order', 'purchase.order', 'account.invoice', 'stock.picking', 'crm.lead',
                                   'project.issue', 'of.service', 'of.planning.intervention'):
                record = self.env[res.res_model].browse(res.res_id)
                if record.partner_id:
                    # Check existence of partner directory
                    top_partner = record.partner_id
                    while top_partner.parent_id:
                        top_partner = top_partner.parent_id
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
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
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    self.env['muk_dms.file'].create({'name': res.name,
                                                     'directory': partner_dir.id,
                                                     'of_file_type': 'related',
                                                     'of_related_model': res.res_model,
                                                     'of_related_id': res.res_id,
                                                     'of_attachment_id': res.id,
                                                     'size': res.file_size})
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
