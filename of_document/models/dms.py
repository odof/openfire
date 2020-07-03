# -*- coding: utf-8 -*-

import unidecode
import itertools
from collections import defaultdict

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.addons.muk_dms.models import dms_base


class Directory(dms_base.DMSModel):
    _inherit = 'muk_dms.directory'

    of_partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire associé")
    of_is_protected = fields.Boolean(string=u"Répertoire protégé")
    # Correction d'erreur sur le recalcul de relational_path sur plusieurs niveaux
    relational_path = fields.Text(recursive=True)

    @api.constrains('name')
    def _check_name(self):
        if not self.check_name(self.name):
            raise ValidationError(u"Le nom de répertoire n'est pas valide : %s" % self.name)

    def _before_create(self, vals):
        vals = super(Directory, self)._before_create(vals)
        if 'name' in vals:
            vals['name'] = vals['name'].replace('/', '|').lstrip()
        return vals

    @api.model
    def of_get_partner_parent_directory(self, partner):
        # Find parent directory
        partner_first_char = (unidecode.unidecode(partner.name[0])).lower()
        if partner_first_char.isalpha():
            try:
                parent_dir = self.env.ref('of_document.' + partner_first_char + '_partner_directory')
            except:
                parent_dir = self.env.ref('of_document.other_partner_directory')
        else:
            parent_dir = self.env.ref('of_document.other_partner_directory')
        return parent_dir

    @api.model
    def of_get_partner_directory(self, partner):
        """
        Récupère le dossier du partenaire ou en crée un si nécessaire.
        :param partner: Partenaire dont on cherche le dossier
        :return: Dossier du partenaire
        """
        dms_dir_obj = self.env['muk_dms.directory']
        top_partner = partner.commercial_partner_id
        top_partner_dir = dms_dir_obj.search([('of_partner_id', '=', top_partner.id)])
        if not top_partner_dir:
            parent_dir = self.of_get_partner_parent_directory(top_partner)
            # Create partner directory
            top_partner_dir = dms_dir_obj.create({'name': top_partner.name,
                                                  'parent_directory': parent_dir.id,
                                                  'of_partner_id': top_partner.id})
        return top_partner_dir


class File(dms_base.DMSModel):
    _name = 'muk_dms.file'
    _inherit = ['muk_dms.file', 'mail.thread']

    @api.model
    def _init_files(self):
        for partner in self.env['res.partner'].search([]):

            objects = [('of_document.res_partner_file_category', partner)]
            for obj_name in ('sale.order', 'purchase.order', 'crm.lead', 'project.issue', 'of.service',
                             'of.planning.intervention'):
                objects.append((
                    'of_document.%s_file_category' % obj_name.replace('.', '_'),
                    self.env[obj_name].search([('partner_id', '=', partner.id)])))
            objects.append(('of_document.account_invoice_out_file_category',
                            self.env['account.invoice'].search([('partner_id', '=', partner.id),
                                                                ('type', 'in', ('out_invoice', 'out_refund'))])))
            objects.append(('of_document.account_invoice_in_file_category',
                            self.env['account.invoice'].search([('partner_id', '=', partner.id),
                                                                ('type', 'in', ('in_invoice', 'in_refund'))])))
            objects.append(('of_document.stock_picking_out_file_category',
                            self.env['stock.picking'].search([('partner_id', '=', partner.id),
                                                              ('picking_type_id.code', '=', 'outgoing')])))
            objects.append(('of_document.stock_picking_in_file_category',
                            self.env['stock.picking'].search([('partner_id', '=', partner.id),
                                                              ('picking_type_id.code', '=', 'incoming')])))
            partner_dir = False
            for categ, obj in objects:
                attachments = self.env['ir.attachment'].\
                    search([('res_model', '=', obj._name), ('res_id', 'in', obj.ids)])
                if not attachments:
                    continue

                if not partner_dir:
                    partner_dir = self.env['muk_dms.directory'].of_get_partner_directory(partner)

                categ = self.env.ref(categ)
                for attachment in attachments:
                    self.create({'name': attachment.name,
                                 'directory': partner_dir.id,
                                 'of_file_type': 'related',
                                 'of_related_model': obj._name,
                                 'of_related_id': attachment.res_id,
                                 'of_attachment_id': attachment.id,
                                 'of_attachment_partner_id': partner.id,
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
    of_attachment_partner_id = fields.Many2one('res.partner', readonly=True, string=u"Contact de la pièce jointe")

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

    @api.model
    def of_get_object_partner_and_category(self, obj):
        partner = False
        categ_ref = False
        if obj._name == 'res.partner':
            partner = obj
            categ_ref = 'res_partner'
        elif obj._name in ('sale.order', 'purchase.order', 'account.invoice', 'stock.picking', 'crm.lead',
                           'project.issue', 'of.service', 'of.planning.intervention'):
            partner = obj.partner_id
            categ_ref = obj._name.replace('.', '_')

            if obj._name == 'account.invoice':
                if obj.type in ('out_invoice', 'out_refund'):
                    categ_ref += '_out'
                else:
                    categ_ref += '_in'
            elif obj._name == 'stock.picking':
                if obj.picking_type_id.code == 'outgoing':
                    categ_ref += '_out'
                elif obj.picking_type_id.code == 'incoming':
                    categ_ref += '_in'
                else:
                    partner = categ_ref = False
        categ = categ_ref and self.env.ref('of_document.' + categ_ref + '_file_category')
        return partner, categ

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
        attachments = self.env['ir.attachment']
        for dms_file in self:
            if dms_file.of_file_type == 'related':
                attachments |= dms_file.of_attachment_id

        res = super(File, self).unlink()
        attachments.unlink()
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
        if self._uid != SUPERUSER_ID and ids:
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

        return len(orig_ids) if count else orig_ids


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
