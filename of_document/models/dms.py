# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.muk_dms.models import dms_base


class Directory(dms_base.DMSModel):
    _inherit = 'muk_dms.directory'

    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire associé")


class File(dms_base.DMSModel):
    _inherit = 'muk_dms.file'

    @api.model
    def _init_files(self):
        main_dir = self.env.ref('of_document.main_partner_directory')
        partners = self.env['res.partner'].search([])
        for partner in partners:
            partner_dir = False
            # Partner attachments
            attachments = self.env['ir.attachment'].\
                search([('res_model', '=', 'res.partner'), ('res_id', '=', partner.id)])
            if attachments:
                # Create customer directory
                partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                    'parent_directory': main_dir.id,
                                                                    'partner_id': partner.id})
                for attachment in attachments:
                    self.create({'name': attachment.name,
                                 'directory': partner_dir.id,
                                 'of_file_type': 'related',
                                 'of_related_model': 'res.partner',
                                 'of_related_id': partner.id,
                                 'of_attachment_id': attachment.id})
            # Sale order attachments
            sale_orders = self.env['sale.order'].search([('partner_id', '=', partner.id)])
            for sale_order in sale_orders:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'sale.order'), ('res_id', '=', sale_order.id)])
                if attachments:
                    if not partner_dir:
                        # Create customer directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                            'parent_directory': main_dir.id,
                                                                            'partner_id': partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'sale.order',
                                     'of_related_id': sale_order.id,
                                     'of_attachment_id': attachment.id})
            # Purchase order attachments
            purchase_orders = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
            for purchase_order in purchase_orders:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'purchase.order'), ('res_id', '=', purchase_order.id)])
                if attachments:
                    if not partner_dir:
                        # Create customer directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                            'parent_directory': main_dir.id,
                                                                            'partner_id': partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'purchase.order',
                                     'of_related_id': purchase_order.id,
                                     'of_attachment_id': attachment.id})
            # Invoice attachments
            invoices = self.env['account.invoice'].search([('partner_id', '=', partner.id)])
            for invoice in invoices:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'account.invoice'), ('res_id', '=', invoice.id)])
                if attachments:
                    if not partner_dir:
                        # Create customer directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                            'parent_directory': main_dir.id,
                                                                            'partner_id': partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'account.invoice',
                                     'of_related_id': invoice.id,
                                     'of_attachment_id': attachment.id})
            # Picking attachments
            pickings = self.env['stock.picking'].search([('partner_id', '=', partner.id)])
            for picking in pickings:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)])
                if attachments:
                    if not partner_dir:
                        # Create customer directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                            'parent_directory': main_dir.id,
                                                                            'partner_id': partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'stock.picking',
                                     'of_related_id': picking.id,
                                     'of_attachment_id': attachment.id})
            # Lead attachments
            leads = self.env['crm.lead'].search([('partner_id', '=', partner.id)])
            for lead in leads:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)])
                if attachments:
                    if not partner_dir:
                        # Create customer directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                            'parent_directory': main_dir.id,
                                                                            'partner_id': partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'crm.lead',
                                     'of_related_id': lead.id,
                                     'of_attachment_id': attachment.id})
            # Project issue attachments
            issues = self.env['project.issue'].search([('partner_id', '=', partner.id)])
            for issue in issues:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'project.issue'), ('res_id', '=', issue.id)])
                if attachments:
                    if not partner_dir:
                        # Create customer directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                            'parent_directory': main_dir.id,
                                                                            'partner_id': partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'project.issue',
                                     'of_related_id': issue.id,
                                     'of_attachment_id': attachment.id})
            # Service attachments
            services = self.env['of.service'].search([('partner_id', '=', partner.id)])
            for service in services:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'of.service'), ('res_id', '=', service.id)])
                if attachments:
                    if not partner_dir:
                        # Create customer directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': partner.name,
                                                                            'parent_directory': main_dir.id,
                                                                            'partner_id': partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'of.service',
                                     'of_related_id': service.id,
                                     'of_attachment_id': attachment.id})

    of_file_type = fields.Selection(
        selection=[('normal', u"Fichier normal"), ('related', u"Fichier lié")], string=u"Type de fichier",
        default='normal')
    of_related_model = fields.Char(string=u"Modèle de document concerné")
    of_related_id = fields.Integer(string=u"ID du document associé")
    of_attachment_id = fields.Many2one(comodel_name='ir.attachment', string=u"Pièce jointe associée")

    def _get_content(self):
        self.ensure_one()
        self.check_access('read', raise_exception=True)
        if self.of_file_type == 'normal':
            return self.reference.sudo().content() if self.reference else None
        elif self.of_file_type == 'related':
            return self.of_attachment_id.datas if self.of_attachment_id else None


class DatabaseDataModel(models.Model):
    _inherit = 'muk_dms.data_database'

    data = fields.Binary(string="Content", attachment=True)
