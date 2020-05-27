# -*- coding: utf-8 -*-

import unidecode

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.muk_dms.models import dms_base


class Directory(dms_base.DMSModel):
    _inherit = 'muk_dms.directory'

    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire associé")

    @api.constrains('name')
    def _check_name(self):
        if not self.check_name(self.name):
            raise ValidationError("The directory name is invalid.")


class File(dms_base.DMSModel):
    _name = 'muk_dms.file'
    _inherit = ['muk_dms.file', 'mail.thread']

    @api.model
    def _init_files(self):
        partners = self.env['res.partner'].search([])
        for partner in partners:
            # Find parent directory

            # All attachments are set to top partner directory
            top_partner = partner
            while top_partner.parent_id:
                top_partner = top_partner.parent_id

            top_partner_first_char = (unidecode.unidecode(top_partner.name[0])).lower()
            if top_partner_first_char.isalpha():
                try:
                    parent_dir = self.env.ref('of_document.' + top_partner_first_char + '_partner_directory')
                except:
                    parent_dir = self.env.ref('of_document.other_partner_directory')
            else:
                parent_dir = self.env.ref('of_document.other_partner_directory')

            partner_dir = False

            # Partner attachments
            attachments = self.env['ir.attachment'].\
                search([('res_model', '=', 'res.partner'), ('res_id', '=', partner.id)])
            if attachments:
                # Check existence of top partner directory
                partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                if not partner_dir:
                    # Create partner directory
                    partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                        'parent_directory': parent_dir.id,
                                                                        'partner_id': top_partner.id})
                for attachment in attachments:
                    self.create({'name': attachment.name,
                                 'directory': partner_dir.id,
                                 'of_file_type': 'related',
                                 'of_related_model': 'res.partner',
                                 'of_related_id': partner.id,
                                 'of_attachment_id': attachment.id,
                                 'size': attachment.file_size})
            # Sale order attachments
            sale_orders = self.env['sale.order'].search([('partner_id', '=', partner.id)])
            for sale_order in sale_orders:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'sale.order'), ('res_id', '=', sale_order.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'sale.order',
                                     'of_related_id': sale_order.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})
            # Purchase order attachments
            purchase_orders = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
            for purchase_order in purchase_orders:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'purchase.order'), ('res_id', '=', purchase_order.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'purchase.order',
                                     'of_related_id': purchase_order.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})
            # Invoice attachments
            invoices = self.env['account.invoice'].search([('partner_id', '=', partner.id)])
            for invoice in invoices:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'account.invoice'), ('res_id', '=', invoice.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'account.invoice',
                                     'of_related_id': invoice.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})
            # Picking attachments
            pickings = self.env['stock.picking'].search([('partner_id', '=', partner.id)])
            for picking in pickings:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'stock.picking',
                                     'of_related_id': picking.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})
            # Lead attachments
            leads = self.env['crm.lead'].search([('partner_id', '=', partner.id)])
            for lead in leads:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'crm.lead',
                                     'of_related_id': lead.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})
            # Project issue attachments
            issues = self.env['project.issue'].search([('partner_id', '=', partner.id)])
            for issue in issues:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'project.issue'), ('res_id', '=', issue.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'project.issue',
                                     'of_related_id': issue.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})
            # Service attachments
            services = self.env['of.service'].search([('partner_id', '=', partner.id)])
            for service in services:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'of.service'), ('res_id', '=', service.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'of.service',
                                     'of_related_id': service.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})
            # Planning intervention attachments
            interventions = self.env['of.planning.intervention'].search([('partner_id', '=', partner.id)])
            for intervention in interventions:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'of.planning.intervention'), ('res_id', '=', intervention.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'partner_id': top_partner.id})
                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'of.planning.intervention',
                                     'of_related_id': intervention.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size})

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

    @api.multi
    def action_view_linked_record(self):
        self.ensure_one()
        if self.of_file_type == 'related':
            view_id = False
            if self.of_related_model == 'res.partner':
                view_id = self.env.ref('base.view_partner_form').id
            elif self.of_related_model == 'sale.order':
                view_id = self.env.ref('sale.view_order_form').id
            elif self.of_related_model == 'purchase.order':
                view_id = self.env.ref('purchase.purchase_order_form').id
            elif self.of_related_model == 'account.invoice':
                invoice = self.env['account.invoice'].browse(self.of_related_id)
                if invoice.type in ('out_invoice', 'out_refund'):
                    view_id = self.env.ref('account.invoice_form').id
                else:
                    view_id = self.env.ref('account.invoice_supplier_form').id
            elif self.of_related_model == 'stock.picking':
                view_id = self.env.ref('stock.view_picking_form').id
            elif self.of_related_model == 'crm.lead':
                view_id = self.env.ref('crm.crm_case_form_view_oppor').id
            elif self.of_related_model == 'project.issue':
                view_id = self.env.ref('project_issue.project_issue_form_view').id
            elif self.of_related_model == 'of.service':
                view_id = self.env.ref('of_service.view_of_service_form').id
            elif self.of_related_model == 'of.planning.intervention':
                view_id = self.env.ref('of_planning.of_planning_intervention_view_form').id
            return {
                'name': u"Objet lié",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': self.of_related_model,
                'res_id': self.of_related_id,
            }

    @api.multi
    def unlink(self):
        # Automatically delete ir.attachment if related file
        attachment_ids_list = []
        for dms_file in self:
            if dms_file.of_file_type == 'related':
                attachment_ids_list.append(dms_file.of_attachment_id.id)

        res = super(File, self).unlink()

        if attachment_ids_list:
            self.env['ir.attachment'].browse(attachment_ids_list).unlink()

        return res


class DatabaseDataModel(models.Model):
    _inherit = 'muk_dms.data_database'

    data = fields.Binary(string="Content", attachment=True)
