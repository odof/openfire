# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from unidecode import unidecode

from odoo import SUPERUSER_ID, _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError
from odoo.tools import frozendict


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _default_of_type_selection(self):
        return "web"

    of_user_type = fields.Selection(
        selection=[
            ("web", "Web"),
            ("technical", "Technical"),
            ("external", "External"),
            ("inactive", "Inactive resource"),
        ],
        string="User type",
        default=lambda u: u._default_of_type_selection(),
    )
    of_reactivated_user = fields.Boolean(string="Reactivated user")

    @api.model
    @tools.ormcache("self._uid")
    def context_get(self):
        # Pour désactiver l'envoi des notifications par courriel des changements d'affectation des commandes
        # et factures. On met par défaut dans le contexte des utilisateurs la valeur mail_auto_subscribe_no_notify
        # qui inhibe l'envoi des notifications dans la fonction _message_auto_subscribe_notify()
        # de /addons/mail/models.mail_thread.py.
        frozen_context = super().context_get()
        new_context = dict(frozen_context)
        new_context["mail_auto_subscribe_no_notify"] = 1
        return frozendict(new_context)

    def _get_default_email(self):
        self.ensure_one()
        return re.sub("[^a-zA-Z0-9._%+-]", "", unidecode(self.partner_id.name)).lower() + "@example.com"

    def write(self, values):
        if SUPERUSER_ID in self._ids and self._uid != SUPERUSER_ID:
            raise AccessError(
                _("Only the administrator account can modify the information of the administrator account.")
            )
        # save current inactive users to check if they are reactivated
        inactive_users = self.browse()
        if values.get("active"):
            inactive_users = self.filtered(lambda u: not u.active)
        result = super().write(values)
        # mark reactivated users as such
        if inactive_users and values.get("active"):
            inactive_users.write({"of_reactivated_user": True})

        # check that we don't add the group of_group_root_only to a user that is not an admin
        group_root = self.env.ref("of_base.of_group_root_only").sudo()
        self._check_admin_only_group()

        if not len(group_root.users):
            raise UserError(_('The group "%s" cannot be removed from the administrator account.') % group_root.name)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._check_admin_only_group()
        for user in users:
            if not user.email:
                user.email = user._get_default_email()
        return user

    def action_send_notifications(self, notifications):
        """
        Fonction pour envoyer des notifications aux utilisateurs connectés, à la fois dans le backoffice
        et vers des systèmes de notifications externes (comme Firebase)
        Le format du message suit en premier lieu les besoins des notifications internes de Odoo pour le backoffice
        {
            'backoffice : {
                'message': STRING,
                'message_is_html': BOOLEAN,
                'sticky' : BOOLEAN,
                'title' : STRING,
                'warning': BOOLEAN,
            }
        }
        Si besoin d'envoyer vers des notifications externes :

        Par exemple pour Firebase :
            'firebase' : {
                'user_ids' : list ids,
                'kind' : 'data' ou 'message_with_data',
                'title' : STRING, (si message_with_data)
                'message': STRING, (si message_with_data)
                'payload': JSON
            }

        """

        for user in self:
            for notification_type in notifications:
                if notification_type == "backoffice":
                    self.env["bus.bus"]._sendone(
                        user.partner_id,
                        "simple_notification",
                        notifications[notification_type],
                    )
                else:
                    self.env["bus.bus"]._sendone(
                        user.partner_id,
                        notification_type,
                        notifications[notification_type],
                    )

    def _check_admin_only_group(self):
        for user in self:
            group_root = self.env.ref("of_base.of_group_root_only").sudo()
            if group_root in user.groups_id and user not in self.env.ref("base.user_root") | self.env.ref(
                "base.user_admin"
            ):
                raise UserError(_('Only the admin account can belong to group "%s".') % group_root.name)
