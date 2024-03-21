# -*- coding: utf-8 -*-

import re
from odoo import models, api, fields, registry

from odoo.addons.mail.models.mail_mail import MailMail


@api.multi
def _postprocess_sent_message(self, mail_sent=True):
    """Perform any post-processing necessary after sending ``mail``
    successfully, including deleting it completely along with its
    attachment if the ``auto_delete`` flag of the mail was set.
    Overridden by subclasses for extra post-processing behaviors.

    :param browse_record mail: the mail that was just sent
    :return: True
    """
    notif_emails = self.filtered(lambda email: email.notification)
    if notif_emails:
        notifications = self.env['mail.notification'].search([
            ('mail_message_id', 'in', notif_emails.mapped('mail_message_id').ids),
            ('is_email', '=', True)])
        # DEBUT MODIFICATION OPENFIRE
        # Les notifications pour les utilisateurs ont déjà pu être supprimées par le JS (set_message_done)
        # provoquant une exception lors de la mise à jour
        # Utilisation d'un nouveau curseur db dédié
        user_notifications = notifications.filtered(lambda n: not n.res_partner_id.partner_share)
        if user_notifications:
            with registry(self._cr.dbname).cursor() as cr_temp:
                for notif in user_notifications.with_env(self.env(cr=cr_temp)):
                    try:
                        if mail_sent:
                            notif.write({
                                'email_status': 'sent',
                            })
                        else:
                            notif.write({
                                'email_status': 'exception',
                            })
                        cr_temp.commit()
                    except Exception:
                        cr_temp.rollback()

        other_notifications = notifications - user_notifications
        if mail_sent:
            other_notifications.write({
                'email_status': 'sent',
            })
        else:
            other_notifications.write({
                'email_status': 'exception',
            })
        # FIN MODIFICATION OPENFIRE
    if mail_sent:
        self.sudo().filtered(lambda self: self.auto_delete).unlink()
    return True


MailMail._postprocess_sent_message = _postprocess_sent_message


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None, smtp_debug=False):
        if not mail_server_id and not smtp_server:
            # Recherche de serveur de mails par pertinence
            email_from = dict(message._headers).get('From', False)
            if email_from:
                re_match = re.search(r' <(.*?)>', email_from)
                if re_match:
                    # email_from de la forme "nom <prefix@domain>". On extrait l'adresse.
                    email_from = re_match.groups()[0]
                email_from = email_from.strip()
                email_split = email_from.split('@')
                if len(email_split) == 2:
                    prefix, domain = email_split
                    servers = self.sudo().search([('smtp_host', '=like', '%' + domain)], order='sequence')
                    if not servers:
                        servers = self.sudo().search([], order='sequence')
                    if len(servers) > 1:
                        servers = self.sudo().search(
                            [('id', 'in', servers.ids), ('smtp_user', 'in', (prefix, email_from))],
                            order='sequence', limit=1
                        ) or servers
                    mail_server_id = servers[:1].id
        return super(IrMailServer, self).send_email(
            message, mail_server_id=mail_server_id, smtp_server=smtp_server, smtp_port=smtp_port,
            smtp_user=smtp_user, smtp_password=smtp_password, smtp_encryption=smtp_encryption, smtp_debug=smtp_debug)


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    # Store True pour éviter le recalcul lors de l'appui sur n'importe quel bouton.
    of_computed_body = fields.Html(string=u'Contenu calculé', compute='_compute_of_computed_body', sanitize_style=True, strip_classes=True, store=True)

    # Calcul des champs dans mail, mail_compose_message.py : render_message()
    @api.depends()
    def _compute_of_computed_body(self):
        for composer in self:
            if composer.res_id:
                composer.of_computed_body = composer.render_message([composer.res_id])[composer.res_id]['body']

    @api.multi
    def button_reload_computed_body(self):
        self._compute_of_computed_body()
        return {"type": "ir.actions.do_nothing"}

    # Permet à l'auteur du mail de le recevoir en copie si le paramètre du modèle est vrai.
    @api.multi
    def send_mail_action(self):
        res = super(MailComposer, self.with_context(mail_notify_author=self.template_id and self.template_id.of_copie_expediteur)).send_mail_action()
        return res


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    of_copie_expediteur = fields.Boolean(string=u"Copie du mail à l'expéditeur")

    @api.multi
    def create_action(self):
        return super(MailTemplate, self.sudo()).create_action()

    @api.multi
    def unlink_action(self):
        return super(MailTemplate, self.sudo()).unlink_action()


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _search_of_state(self, operator, value):
        messages = self.env['mail.mail'].search([('state', operator, value)]).mapped('mail_message_id')
        return [('id', 'in', messages.ids)]

    of_state = fields.Selection(selection=[
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('exception', 'Delivery Failed'),
        ('cancel', 'Cancelled'),
    ], string=u"Status", compute='_compute_of_state', search='_search_of_state')
    of_failure_reason = fields.Text(
        string=u"Failure Reason", compute='_compute_of_state',
        help="Failure reason. This is usually the exception thrown by the email server, "
             "stored to ease the debugging of mailing issues.")

    @api.multi
    def _compute_of_state(self):
        mail_obj = self.env['mail.mail']
        for message in self:
            mail = mail_obj.search([('mail_message_id', '=', message.id)], limit=1)
            if mail:
                message.of_state = mail.state
                message.of_failure_reason = mail.failure_reason

    @api.model
    def _get_default_from(self):
        if not self.env.user.email:
            self.env.user.email = self.env.user._get_default_email()
        return super(MailMessage, self)._get_default_from()
