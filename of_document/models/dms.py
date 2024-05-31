# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import itertools
from collections import defaultdict
from string import ascii_lowercase

import unidecode

from odoo import SUPERUSER_ID, api, fields, models
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

    def _before_write(self, vals, operation):
        vals = super(Directory, self)._before_write(vals, operation)
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
            except Exception:
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
        top_partner = partner.commercial_partner_id
        top_partner_dir = self.search([('of_partner_id', '=', top_partner.id)], limit=1)
        if not top_partner_dir:
            parent_dir = self.of_get_partner_parent_directory(top_partner)
            # Create partner directory
            top_partner_dir = self.sudo().create({
                'name': top_partner.name,
                'parent_directory': parent_dir.id,
                'of_partner_id': top_partner.id})
        return top_partner_dir

    @api.model
    def of_get_object_directory(self, partner_dir, categ):
        """
        Récupère le sous dossier du partenaire en fonction du nom ou le crée si nécessaire.
        :param partner: Partenaire dont on cherche le sous dossier
        :param categ: Catégorie dont on cherche le dossier
        :return: Sous dossier du partenaire
        """
        default_settings = self.env.ref('of_document.default_settings')
        data = default_settings.of_subdirectory_ids.filtered(lambda d: categ in d.datas_ids)[:1]
        object_dir = self.search(
            [
                ('name', '=', data.name),
                ('parent_directory', '=', partner_dir.id),
            ],
            limit=1
        )
        if not object_dir:
            # Create object directory
            object_dir = self.sudo().create({
                'name': data.name,
                'parent_directory': partner_dir.id,
            })
        return object_dir


class File(dms_base.DMSModel):
    _name = 'muk_dms.file'
    _inherit = ['muk_dms.file', 'mail.thread']

    @api.model
    def _init_files(self):
        cr = self.env.cr
        default_settings = self.env.ref('of_document.default_settings')
        data_ids = default_settings.of_subdirectory_ids.mapped('data_ids')
        dms_dir_obj = self.env['muk_dms.directory']

        def create_muk_directory(parent_dir_id, name, partner_id):
            cr.execute(
                """
                INSERT INTO muk_dms_directory (
                    create_uid,
                    create_date,
                    name,
                    of_partner_id,
                    parent_directory
                )
                VALUES (
                    1,
                    NOW(),
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (name, partner_id, parent_dir_id)
            )
            return cr.fetchone()[0]

        partner_dir_dict = {
            c: self.env.ref('of_document.' + c + '_partner_directory')
            for c in ascii_lowercase
        }
        partner_default_dir = self.env.ref('of_document.other_partner_directory')
        partner_query = """
            SELECT p.id, cp.id, cp.name, p.id, a.id, a.name, a.file_size, a.mimetype
            FROM ir_attachment AS a
            INNER JOIN res_partner AS p ON p.id = a.res_id
            INNER JOIN res_partner AS cp ON cp.id = p.commercial_partner_id
            WHERE a.res_model = 'res.partner' AND a.res_field IS NULL AND p.name IS NOT NULL AND p.name != ''
            ORDER BY cp.id, res_id
        """
        object_query = """
            SELECT p.id, cp.id, cp.name, tab.id, a.id, a.name, a.file_size, a.mimetype
            FROM ir_attachment AS a
            INNER JOIN %s AS tab ON tab.id = a.res_id
            INNER JOIN res_partner AS p ON p.id = tab.partner_id
            INNER JOIN res_partner AS cp ON cp.id = p.commercial_partner_id
            WHERE a.res_model = '%s' AND a.res_field IS NULL AND p.name IS NOT NULL AND p.name != '' %s
            ORDER BY cp.id, p.id
        """
        picking_type_in_ids = self.env['stock.picking.type'].search([('code', '=', 'incoming')]).ids
        picking_type_out_ids = self.env['stock.picking.type'].search([('code', '=', 'outgoing')]).ids
        objects = [
            ('of_document.res_partner_file_category', 'res.partner', ""),
            (
                'of_document.account_invoice_out_file_category',
                'account.invoice',
                "AND tab.type IN ('out_invoice', 'out_refund')",
            ),
            (
                'of_document.account_invoice_in_file_category',
                'account.invoice',
                "AND tab.type IN ('in_invoice', 'in_refund')",
            ),
            (
                'of_document.stock_picking_out_file_category',
                'stock.picking',
                "AND picking_type_id IN " + str(tuple(picking_type_out_ids)),
            ),
            (
                'of_document.stock_picking_in_file_category',
                'stock.picking',
                "AND picking_type_id IN " + str(tuple(picking_type_in_ids)),
            ),
        ]

        for obj_name in (
            'sale.order', 'purchase.order', 'crm.lead', 'project.issue', 'of.service', 'of.planning.intervention'
        ):
            objects.append((
                'of_document.%s_file_category' % obj_name.replace('.', '_'),
                obj_name,
                "",
            ))

        for categ, obj_name, where_query in objects:
            categ = self.env.ref(categ)
            categ_dir_name = False
            if categ in data_ids:
                categ_dir_name = default_settings.of_subdirectory_ids.filtered(lambda d: categ in d.data_ids)[:1].name
            if obj_name == 'res.partner':
                query = partner_query
            else:
                query = object_query % (self.env[obj_name]._table, obj_name, where_query)
            cr.execute(query)
            prev_partner_id = False

            for (
                partner_id, top_partner_id, top_partner_name, res_id, attachment_id, attachment_name, file_size,
                mimetype
            ) in cr.fetchall():
                if top_partner_id != prev_partner_id:
                    # Récupération ou création du répertoire muk
                    prev_partner_id = top_partner_id
                    partner_dir_id = dms_dir_obj.search([('of_partner_id', '=', top_partner_id)], limit=1).id
                    if not partner_dir_id:
                        partner_first_char = top_partner_name and top_partner_name[0].lower()
                        parent_dir = partner_dir_dict.get(partner_first_char, partner_default_dir)
                        partner_dir_id = create_muk_directory(parent_dir.id, top_partner_name, top_partner_id)

                    categ_dir_id = False
                    if categ_dir_name:
                        # Récupération ou création de sous-répertoire muk
                        categ_dir_id = dms_dir_obj.search(
                            [('name', '=', categ_dir_name), ('parent_directory', '=', partner_dir_id)],
                            limit=1
                        ).id
                        if not categ_dir_id:
                            categ_dir_id = create_muk_directory(partner_dir_id, categ_dir_name, None)

                muk_file = self.search(
                    [
                        ('of_related_model', '=', obj_name),
                        ('of_related_id', '=', res_id),
                        ('of_attachment_id', '=', attachment_id),
                        ('of_attachment_partner_id', '=', partner_id),
                    ], limit=1
                )
                if not muk_file:
                    cr.execute(
                        """
                        INSERT INTO muk_dms_file (
                            create_uid,
                            create_date,
                            name,
                            directory,
                            of_file_type,
                            of_related_model,
                            of_related_id,
                            of_attachment_id,
                            of_attachment_partner_id,
                            size,
                            mimetype,
                            of_category_id
                        )
                        VALUES (
                            1,
                            NOW(),
                            %s,  -- name
                            %s,  -- directory
                            'related',
                            %s,  -- of_related_model
                            %s,  -- of_related_id
                            %s,  -- of_attachment_id
                            %s,  -- of_attachment_partner_id
                            %s,  -- size
                            %s,  -- mimetype
                            %s   -- of_category_id
                        )
                        """, (
                            attachment_name,
                            categ_dir_id or partner_dir_id,
                            obj_name,
                            res_id,
                            attachment_id,
                            partner_id,
                            file_size,
                            mimetype,
                            categ.id,
                        ))
                else:
                    cr.execute(
                        """
                        UPDATE muk_dms_file SET
                            name = %s,
                            directory = %s,
                            of_file_type = 'related',
                            size = %s,
                            of_category_id = %s
                        WHERE id = %s
                        """, (
                            attachment_name,
                            categ_dir_id or partner_dir_id,
                            file_size,
                            categ.id,
                            muk_file.id
                        )
                    )
        dms_dir_obj._parent_store_compute()

    of_file_type = fields.Selection(
        selection=[('normal', u"Fichier normal"), ('related', u"Fichier lié")], string=u"Type de fichier",
        default='normal')
    of_related_model = fields.Char(string=u"Modèle de document concerné")
    of_related_id = fields.Integer(string=u"ID du document associé")
    of_attachment_id = fields.Many2one(comodel_name='ir.attachment', string=u"Pièce jointe associée", index=True)
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

    def _before_write(self, vals, operation):
        vals = super(File, self)._before_write(vals, operation)
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
            if len(orig_ids) == limit and len(result) < self._context.get('need', limit):
                need = self._context.get('need', limit) - len(result)
                more_ids = self.with_context(need=need)._search(
                    args, offset=offset + len(orig_ids), limit=limit, order=order, access_rights_uid=access_rights_uid,
                )
                result.extend(list(more_ids)[:limit - len(result)])
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


class MukDmsDirectoryTemplate(models.Model):
    _name = 'of.muk.dms.directory.template'
    _description = u"Modèle de répertoire"

    name = fields.Char(string=u"Titre")
    data_ids = fields.Many2many(comodel_name='of.document.file.category', string=u"Objet(s)")
    parent_id = fields.Many2one(comodel_name='of.muk.dms.directory.template', string=u"Répertoire parent")
    muk_setting_id = fields.Many2one(comodel_name='muk_dms.settings', string=u"Paramètre Muk")


class Settings(dms_base.DMSModel):
    _inherit = 'muk_dms.settings'

    of_default_template = fields.Boolean(
        string=u"Modèle par défaut",
        help=u"Permet de définir s’il s’agit du modèle par "
             u"défaut qui s’applique à la création d’un nouveau répertoire ")
    of_source_directory_id = fields.Many2one(comodel_name='muk_dms.directory', string=u"Répertoire source")
    of_subdirectory_ids = fields.One2many(
        comodel_name='of.muk.dms.directory.template', inverse_name='muk_setting_id', string=u"Sous-répertoires")

    def action_init_files(self):
        self.env['muk_dms.file']._init_files()
