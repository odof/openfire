# -*- coding: utf-8 -*-

import unidecode
import itertools
from collections import defaultdict

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.muk_dms.models import dms_base


class Directory(dms_base.DMSModel):
    _inherit = 'muk_dms.directory'

    of_partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire associé")
    of_is_protected = fields.Boolean(string=u"Répertoire protégé")

    @api.constrains('name')
    def _check_name(self):
        if not self.check_name(self.name):
            raise ValidationError(u"Le nom de répertoire n'est pas valide : %s" % self.name)

    def _before_create(self, vals):
        vals = super(Directory, self)._before_create(vals)
        if 'name' in vals:
            vals['name'] = vals['name'].replace('/', '|').lstrip()
        return vals


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
                partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                if not partner_dir:
                    # Create partner directory
                    partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                        'parent_directory': parent_dir.id,
                                                                        'of_partner_id': top_partner.id})

                # Get partner category
                categ = self.env.ref('of_document.res_partner_file_category')

                for attachment in attachments:
                    self.create({'name': attachment.name,
                                 'directory': partner_dir.id,
                                 'of_file_type': 'related',
                                 'of_related_model': 'res.partner',
                                 'of_related_id': partner.id,
                                 'of_attachment_id': attachment.id,
                                 'size': attachment.file_size,
                                 'of_category_id': categ.id})
            # Sale order attachments
            sale_orders = self.env['sale.order'].search([('partner_id', '=', partner.id)])
            for sale_order in sale_orders:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'sale.order'), ('res_id', '=', sale_order.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get sale order category
                    categ = self.env.ref('of_document.sale_order_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'sale.order',
                                     'of_related_id': sale_order.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})
            # Purchase order attachments
            purchase_orders = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
            for purchase_order in purchase_orders:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'purchase.order'), ('res_id', '=', purchase_order.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get purchase order category
                    categ = self.env.ref('of_document.purchase_order_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'purchase.order',
                                     'of_related_id': purchase_order.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})
            # Invoice attachments
            invoices = self.env['account.invoice'].search([('partner_id', '=', partner.id)])
            for invoice in invoices:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'account.invoice'), ('res_id', '=', invoice.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get invoice category
                    if invoice.type in ('out_invoice', 'out_refund'):
                        categ = self.env.ref('of_document.account_invoice_out_file_category')
                    else:
                        categ = self.env.ref('of_document.account_invoice_in_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'account.invoice',
                                     'of_related_id': invoice.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})
            # Picking attachments
            pickings = self.env['stock.picking'].search([('partner_id', '=', partner.id)])
            for picking in pickings:
                if picking.picking_type_id.code not in ('outgoing', 'incoming'):
                    continue

                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get picking category
                    if picking.picking_type_id.code == 'outgoing':
                        categ = self.env.ref('of_document.stock_picking_out_file_category')
                    else:
                        categ = self.env.ref('of_document.stock_picking_in_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'stock.picking',
                                     'of_related_id': picking.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})
            # Lead attachments
            leads = self.env['crm.lead'].search([('partner_id', '=', partner.id)])
            for lead in leads:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get lead category
                    categ = self.env.ref('of_document.crm_lead_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'crm.lead',
                                     'of_related_id': lead.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})
            # Project issue attachments
            issues = self.env['project.issue'].search([('partner_id', '=', partner.id)])
            for issue in issues:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'project.issue'), ('res_id', '=', issue.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get project issue category
                    categ = self.env.ref('of_document.project_issue_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'project.issue',
                                     'of_related_id': issue.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})
            # Service attachments
            services = self.env['of.service'].search([('partner_id', '=', partner.id)])
            for service in services:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'of.service'), ('res_id', '=', service.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get service category
                    categ = self.env.ref('of_document.of_service_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'of.service',
                                     'of_related_id': service.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})
            # Planning intervention attachments
            interventions = self.env['of.planning.intervention'].search([('partner_id', '=', partner.id)])
            for intervention in interventions:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', 'of.planning.intervention'), ('res_id', '=', intervention.id)])
                if attachments:
                    # Check existence of top partner directory
                    partner_dir = self.env['muk_dms.directory'].search([('of_partner_id', '=', top_partner.id)])
                    if not partner_dir:
                        # Create partner directory
                        partner_dir = self.env['muk_dms.directory'].create({'name': top_partner.name,
                                                                            'parent_directory': parent_dir.id,
                                                                            'of_partner_id': top_partner.id})

                    # Get planning intervention category
                    categ = self.env.ref('of_document.of_planning_intervention_file_category')

                    for attachment in attachments:
                        self.create({'name': attachment.name,
                                     'directory': partner_dir.id,
                                     'of_file_type': 'related',
                                     'of_related_model': 'of.planning.intervention',
                                     'of_related_id': intervention.id,
                                     'of_attachment_id': attachment.id,
                                     'size': attachment.file_size,
                                     'of_category_id': categ.id})

    of_file_type = fields.Selection(
        selection=[('normal', u"Fichier normal"), ('related', u"Fichier lié")], string=u"Type de fichier",
        default='normal')
    of_related_model = fields.Char(string=u"Modèle de document concerné")
    of_related_id = fields.Integer(string=u"ID du document associé")
    of_attachment_id = fields.Many2one(comodel_name='ir.attachment', string=u"Pièce jointe associée")
    of_category_id = fields.Many2one(comodel_name='of.document.file.category', string=u"Catégorie")
    of_tag_ids = fields.Many2many(comodel_name='of.document.file.tag', string=u"Étiquettes")
    of_partner_id = fields.Many2one(comodel_name='res.partner', related='directory.of_partner_id', readonly=True)

    @api.constrains('name')
    def _check_name(self):
        if not self.check_name(self.name):
            raise ValidationError(u"Le nom de fichier n'est pas valide : %s" % self.name)

    def _before_create(self, vals):
        vals = super(File, self)._before_create(vals)
        if 'name' in vals:
            vals['name'] = vals['name'].replace('/', '|').lstrip()
        return vals

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
            if dms_file.of_file_type == 'related' and dms_file.of_attachment_id:
                attachment_ids_list.append(dms_file.of_attachment_id.id)

        res = super(File, self).unlink()

        if attachment_ids_list:
            self.env['ir.attachment'].browse(attachment_ids_list).unlink()

        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        self.check_read()
        return super(File, self).read(fields, load=load)

    @api.model
    def check_read(self):
        """
        Restricts the access to DMS file, according to related model.
        """
        # Collect the records to check (by model)
        model_ids = defaultdict(set)
        self._cr.execute('SELECT of_related_model, of_related_id FROM muk_dms_file WHERE id IN %s',
                         [tuple(self.ids)])
        for res_model, res_id in self._cr.fetchall():
            if res_model:
                model_ids[res_model].add(res_id)

        # Check access rights on the records
        for res_model, res_id in model_ids.iteritems():
            record = self.env[res_model].browse(res_id).exists()
            # For related models, check if we can write to the model, as unlinking
            # and creating attachments can be seen as an update to the model
            record.check_access_rights('read')
            record.check_access_rule('read')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        ids = super(File, self)._search(
            args, offset=offset, limit=limit, order=order, count=False, access_rights_uid=access_rights_uid)
        orig_ids = ids
        ids = set(ids)
        if self._uid != SUPERUSER_ID:
            # For DMS files, the permissions of the document they are attached to
            # apply, so we must remove attachments for which the user cannot access the linked document.
            # Use pure SQL rather than read() as it is about 50% faster for large dbs (100k+ docs),
            # and the permissions are checked in super() and below anyway.
            model_attachments = defaultdict(lambda: defaultdict(set))  # {res_model: {res_id: set(ids)}}
            self._cr.execute("""SELECT id, of_related_model, of_related_id FROM muk_dms_file WHERE id IN %s""",
                             [tuple(ids)])
            for row in self._cr.dictfetchall():
                if not row['of_related_model']:
                    continue
                model_attachments[row['of_related_model']][row['of_related_id']].add(row['id'])

            # To avoid multiple queries for each file found, checks are performed in batch as much as possible.
            for res_model, targets in model_attachments.iteritems():
                if res_model not in self.env:
                    continue
                if not self.env[res_model].check_access_rights('read', False):
                    # Remove all corresponding attachment ids
                    ids.difference_update(itertools.chain(*targets.itervalues()))
                    continue
                # Filter ids according to what access rules permit
                target_ids = list(targets)
                allowed = self.env[res_model].with_context(active_test=False).search([('id', 'in', target_ids)])
                for res_id in set(target_ids).difference(allowed.ids):
                    ids.difference_update(targets[res_id])

            # Sort result according to the original sort ordering
            result = [id for id in orig_ids if id in ids]
            return len(result) if count else list(result)

        return orig_ids


class DatabaseDataModel(models.Model):
    _inherit = 'muk_dms.data_database'

    data = fields.Binary(string="Content", attachment=True)


class FileCategory(models.Model):
    _name = 'of.document.file.category'
    _description = u"Catégorie de fichier"

    name = fields.Char(string=u"Nom", required=True)


class FileTag(models.Model):
    _name = 'of.document.file.tag'
    _description = u"Étiquette de fichier"
    _order = 'name'

    name = fields.Char(string=u"Nom", required=True)
    color = fields.Integer(string=u"Couleur")
