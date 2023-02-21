# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
import logging
from odoo import models, api, tools

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    @api.model
    def send_email(
            self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
            smtp_user=None, smtp_password=None, smtp_encryption=None,
            smtp_ssl_certificate=None, smtp_ssl_private_key=None,
            smtp_debug=False, smtp_session=None):
        """ Override to allow the possibility to disable email sending for testing purpose.
        Also, if no mail_server_id is given, we try to find the best one based on the email_from.
        """
        if tools.config.get('of_disable_email_sending'):
            _logger.warning('Email sending is disabled from the config file')
            return message['Message-Id']
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
                    servers = self.sudo().search([('smtp_host', '=like', f'%{domain}')], order='sequence')
                    if not servers:
                        servers = self.sudo().search([], order='sequence')
                    if len(servers) > 1:
                        servers = self.sudo().search(
                            [('id', 'in', servers.ids), ('smtp_user', 'in', (prefix, email_from))],
                            order='sequence', limit=1
                        ) or servers
                    mail_server_id = servers[:1].id
        return super().send_email(
            message=message, mail_server_id=mail_server_id, smtp_server=smtp_server,
            smtp_port=smtp_port, smtp_user=smtp_user, smtp_password=smtp_password, smtp_encryption=smtp_encryption,
            smtp_ssl_certificate=smtp_ssl_certificate, smtp_ssl_private_key=smtp_ssl_private_key,
            smtp_debug=smtp_debug, smtp_session=smtp_session)

    def build_email(self, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
                    attachments=None, message_id=None, references=None, object_id=False, subtype='plain', headers=None,
                    body_alternative=None, subtype_alternative='plain'):
        """ Override to allow the possibility to force the email_to in the headers for testing purpose.
        """
        if tools.config.get('of_email_to'):
            cfg_email_to = tools.config['of_email_to']
            _logger.warning(f'email_to is forced to {cfg_email_to} from the config file')
            email_to = tools.email_split_and_format(tools.config['of_email_to'])
            email_cc = None
            email_bcc = None
        return super(IrMailServer, self).build_email(
            email_from, email_to, subject, body, email_cc, email_bcc, reply_to, attachments, message_id, references,
            object_id, subtype, headers, body_alternative, subtype_alternative)
