# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import frozendict


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _default_of_type_selection(self):
        return 'web'

    of_user_type = fields.Selection(
        selection='_get_user_type_selection', string="User type",
        default=lambda u: u._default_of_type_selection())

    @api.model
    @tools.ormcache('self._uid')
    def context_get(self):
        # Pour désactiver l'envoi des notifications par courriel des changements d'affectation des commandes
        # et factures. On met par défaut dans le contexte des utilisateurs la valeur mail_auto_subscribe_no_notify
        # qui inhibe l'envoi des notifications dans la fonction _message_auto_subscribe_notify()
        # de /addons/mail/models.mail_thread.py.
        frozen_context = super().context_get()
        new_context = dict(frozen_context)
        new_context['mail_auto_subscribe_no_notify'] = 1
        return frozendict(new_context)

    @api.model
    def _get_user_type_selection(self):
        return [
            ('web', "Web"),
            ('technical', "Technical"),
        ]

    def _get_default_email(self):
        self.ensure_one()
        return self.partner_id.name.lower().replace(" ", "") + "@example.com"

    def write(self, values):
        if SUPERUSER_ID in self._ids and self._uid != SUPERUSER_ID:
            raise AccessError(
                _("Only the administrator account can modify the information of the administrator account."))
        result = super().write(values)
        group_root = self.env.ref('of_base.of_group_root_only').sudo()
        admin_user_id = self.env.ref('base.user_admin').id
        if not len(group_root.users):
            raise UserError(_("The group \"%s\" cannot be removed from the administrator account.") % group_root.name)
        if 'groups_id' in values and (len(group_root.users) > 2 or group_root.users.id != admin_user_id):
            raise UserError(_("Group \"%s\" cannot be added to a user!") % group_root.name)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        for user in users:
            if not user.email:
                user.email = user._get_default_email()
        return user
