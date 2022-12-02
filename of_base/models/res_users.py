# -*- coding: utf-8 -*-

from odoo import models, api, tools, fields, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    of_user_type = fields.Selection(
        selection='_get_user_type_selection', string=u"Type d'utilisateur", default=lambda u: u._default_of_user_type())

    @api.model
    def _get_user_type_selection(self):
        return [
            ('web', u"Web"),
            ('technical', u"Technique"),
        ]

    @api.model
    def _default_of_user_type(self):
        return 'web'

    @api.model
    @tools.ormcache('self._uid')
    def context_get(self):
        # Pour désactiver l'envoi des notifications par courriel des changements d'affectation des commandes
        # et factures. On met par défaut dans le contexte des utilisateurs la valeur mail_auto_subscribe_no_notify
        # qui inhibe l'envoi des notifications dans la fonction _message_auto_subscribe_notify()
        # de /addons/mail/models.mail_thread.py.
        result = super(ResUsers, self).context_get()
        result['mail_auto_subscribe_no_notify'] = 1
        return result

    @api.multi
    def _get_default_email(self):
        self.ensure_one()
        return self.partner_id.name.lower().replace(" ", "") + "@example.com"

    @api.model
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        if not user.email:
            user.email = user._get_default_email()
        return user

    @api.multi
    def write(self, values):
        if SUPERUSER_ID in self._ids and self._uid != SUPERUSER_ID:
            raise AccessError(u'Seul le compte administrateur peut modifier les informations du compte administrateur.')
        result = super(ResUsers, self).write(values)
        group_root = self.env.ref('of_base.of_group_root_only').sudo()
        if not len(group_root.users):
            raise UserError(u'Le groupe "%s" ne peut être retiré du compte administrateur !' % group_root.name)
        if len(group_root.users) > 1 or group_root.users.id != SUPERUSER_ID:
            raise UserError(u'Le groupe "%s" ne peut être ajouté à un utilisateur !' % group_root.name)
        return result
