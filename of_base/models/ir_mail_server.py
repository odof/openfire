# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from odoo import models, api


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    @api.model
    def send_email(
            self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
            smtp_user=None, smtp_password=None, smtp_encryption=None,
            smtp_ssl_certificate=None, smtp_ssl_private_key=None,
            smtp_debug=False, smtp_session=None):
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
