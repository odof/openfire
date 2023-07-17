# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFRecomputeGetPartnersWizard(models.TransientModel):
    _name = 'of.recompute.ged.partners.wizard'

    partner_ids = fields.Many2many(comodel_name='res.partner', string=u"Partenaires")
    field_directory_ids = fields.Many2many(
        comodel_name='ir.model.fields', string=u"Champs des dossiers",
        relation='field_directory_ids_rel',
        domain=lambda s:s._get_field_directory_ids_domain(),
        default=lambda s:s._get_field_directory_ids_defaults(),
        help=u"Path: Permet de recalculer le path complet du dossier, peut faire planter une action qui ajoute "
             u"une PJ et que le path n'est pas correctement calculé.")
    field_file_ids = fields.Many2many(
        comodel_name='ir.model.fields', string=u"Champs des fichiers",
        relation='field_file_ids_rel',
        domain=lambda s:s._get_field_file_ids_domain(),
        default=lambda s:s._get_field_file_ids_defaults(),
        help=u"Path: Permet de recalculer le path complet du fichier, peut faire planter une action qui ajoute "
             u"une PJ et que le path n'est pas correctement calculé.\n"
             u"Fichiers: Permet de recalculer l'extension du fichier, permet d'actualiser la preview des fichiers.\n")

    @api.model
    def _get_field_directory_ids_defaults(self):
        defaults = []
        relational_path = self.env.ref('muk_dms.field_muk_dms_directory_relational_path', raise_if_not_found=False)
        if relational_path:
            defaults.append((4, relational_path.id))
        return defaults

    @api.model
    def _get_field_file_ids_defaults(self):
        defaults = []
        relational_path = self.env.ref('muk_dms.field_muk_dms_file_relational_path', raise_if_not_found=False)
        if relational_path:
            defaults.append((4, relational_path.id))
        extension = self.env.ref('muk_dms.field_muk_dms_file_extension', raise_if_not_found=False)
        if extension:
            defaults.append((4, extension.id))
        return defaults

    @api.model
    def _get_field_directory_ids_domain(self):
        field_ids = []
        relational_path = self.env.ref('muk_dms.field_muk_dms_directory_relational_path', raise_if_not_found=False)
        if relational_path:
            field_ids.append(relational_path.id)
        return [('id', 'in', field_ids)]

    @api.model
    def _get_field_file_ids_domain(self):
        field_ids = []
        relational_path = self.env.ref('muk_dms.field_muk_dms_file_relational_path', raise_if_not_found=False)
        if relational_path:
            field_ids.append(relational_path.id)
        extension = self.env.ref('muk_dms.field_muk_dms_file_extension', raise_if_not_found=False)
        if extension:
            field_ids.append(extension.id)
        return [('id', 'in', field_ids)]

    @api.multi
    def recompute_partners(self):
        muk_directory_obj = self.env['muk_dms.directory']
        domain = [('parent_directory', '!=', False)]
        if self.partner_ids:
            domain += [('of_partner_id', 'in', self.partner_ids._ids)]
        else:
            domain += [('of_partner_id', '!=', False)]
        main_directories = muk_directory_obj.search(domain)

        for partner_directory in main_directories:
            current_directories = partner_directory
            while current_directories:
                # recompute current directories before children, they may need the path
                if self.field_directory_ids:
                    # if field_directory_ids is not False then we know relational_path
                    # need to be recomputed as it is the only field available
                    current_directories._compute_relational_path()
                # recompute files in current directories
                if self.field_file_ids:
                    files = current_directories.mapped('files')
                    for field_name in self.field_file_ids.mapped('name'):
                        files._recompute_todo(files._fields[field_name])
                    files.recompute()
                current_directories = current_directories.mapped('child_directories')
