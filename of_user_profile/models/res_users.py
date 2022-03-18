# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_default_field_ids(self):
        return self.env['ir.model.fields'].search([('model', '=', 'res.users'), ('name', '=', 'groups_id')]).ids

    of_is_user_profile = fields.Boolean(string=u"Est un profil utilisateur ?")
    of_user_profile_id = fields.Many2one(
        comodel_name='res.users', string=u"Profil utilisateur", domain=[('of_is_user_profile', '=', True)],
        context={'active_test': False})
    of_user_ids = fields.One2many(
        comodel_name='res.users', inverse_name='of_user_profile_id', string=u"Utilisateurs",
        domain=[('of_is_user_profile', '=', False)])
    of_field_ids = fields.Many2many(
        comodel_name='ir.model.fields', string=u"Champs à mettre à jour",
        domain=[('model', 'in', ('res.users', 'res.partner')),
                ('ttype', 'not in', ('one2many',)),
                ('name', 'not in', ('of_is_user_profile', 'of_user_profile_id', 'of_user_ids', 'of_field_ids', 'view')),
                ], default=lambda self: self._get_default_field_ids())

    _sql_constraints = [
        ('profile_without_profile_id',
         'CHECK( (of_is_user_profile = TRUE AND of_user_profile_id IS NULL) OR of_is_user_profile = FALSE )',
         u"Un profil utilisateur ne peut pas être lié à un autre profil !"),
    ]

    @api.onchange('of_is_user_profile')
    def onchange_of_is_user_profile(self):
        if self.of_is_user_profile:
            self.active = False
            self.of_user_profile_id = False

    @api.multi
    def _update_from_profile(self, fields=None):
        if not self:
            return
        if len(self.mapped('of_user_profile_id')) != 1:
            raise UserError(u"_update_from_profile accepte uniquement des utilisateurs liés au même profil !")
        user_profile = self[0].of_user_profile_id
        if not fields:
            fields = user_profile.of_field_ids.mapped('name')
        else:
            fields = set(fields) & set(user_profile.of_field_ids.mapped('name'))

        vals = {}
        for field in fields:
            value = getattr(user_profile, field)
            field_type = self._fields[field].type
            if field_type == 'many2one':
                vals[field] = value.id
            elif field_type == 'many2many':
                vals[field] = [(6, 0, value.ids)]
            elif field_type == 'one2many':
                raise UserError(u"_update_from_profile ne gère pas les champs One2many")
            else:
                vals[field] = value
        if vals:
            self.write(vals)

    @api.multi
    def _update_users_linked_to_profile(self, fields=None):
        for user_profile in self.filtered(lambda user: user.of_is_user_profile):
            user_profile.with_context(active_test=False).mapped('of_user_ids')._update_from_profile(fields)

    @api.model
    def create(self, vals):
        record = super(ResUsers, self).create(vals)
        if record.of_user_profile_id:
            record._update_from_profile()
        return record

    @api.multi
    def write(self, vals):
        users_to_update = False
        if vals.get('of_user_profile_id'):
            users_to_update = self.filtered(lambda user: user.of_user_profile_id.id != vals['of_user_profile_id'])
        vals = self._remove_reified_groups(vals)
        res = super(ResUsers, self).write(vals)
        if vals.get('of_user_profile_id'):
            users_to_update._update_from_profile()
        else:
            self._update_users_linked_to_profile(vals.keys())
        return res

    @api.multi
    def copy_data(self, default=None):
        default = default.copy() if default else {}
        default['of_user_ids'] = []
        if self.of_is_user_profile:
            default['of_is_user_profile'] = False
            default['of_user_profile_id'] = self.id
        return super(ResUsers, self).copy_data(default)
