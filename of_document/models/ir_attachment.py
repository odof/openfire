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
                partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
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
                                                                        'of_partner_id': top_partner.id})

                # Get corresponding category
                categ = self.env.ref('of_document.res_partner_file_category')

                # Create DMS file
                self.env['muk_dms.file'].create({'name': res.name,
                                                 'directory': partner_dir.id,
                                                 'of_file_type': 'related',
                                                 'of_related_model': 'res.partner',
                                                 'of_related_id': partner.id,
                                                 'of_attachment_id': res.id,
                                                 'size': res.file_size,
                                                 'of_category_id': categ.id})
            elif res.res_model in ('sale.order', 'purchase.order', 'account.invoice', 'stock.picking', 'crm.lead',
                                   'project.issue', 'of.service', 'of.planning.intervention'):
                record = self.env[res.res_model].browse(res.res_id)

                if res.res_model == 'stock.picking':
                    if record.picking_type_id.code not in ('outgoing', 'incoming'):
                        return res

                if record.partner_id:
                    # Check existence of partner directory
                    top_partner = record.partner_id
                    while top_partner.parent_id:
                        top_partner = top_partner.parent_id
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
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
                                                                            'of_partner_id': top_partner.id})

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
                    self.env['muk_dms.file'].create({'name': res.name,
                                                     'directory': partner_dir.id,
                                                     'of_file_type': 'related',
                                                     'of_related_model': res.res_model,
                                                     'of_related_id': res.res_id,
                                                     'of_attachment_id': res.id,
                                                     'size': res.file_size,
                                                     'of_category_id': categ.id})
            return res

    @api.multi
    def unlink(self):
        # Automatically delete DMS file if partner related attachment
        dms_files_to_delete = self.env['muk_dms.file']
        for attachment in self:
            dms_files_to_delete += self.env['muk_dms.file'].search([('of_attachment_id', '=', attachment.id)])

        res = super(IrAttachment, self).unlink()

        if dms_files_to_delete:
            for dms_file in dms_files_to_delete:
                dms_dir = dms_file.directory
                dms_file.unlink()
                # Delete DMS directory if no file left
                if not dms_dir.files:
                    dms_dir.unlink()

        return res
