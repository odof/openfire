# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import smtplib

from odoo import fields, models


class ESBConnection(models.Model):
    _inherit = 'of.esb.connection'

    ttype = fields.Selection(selection_add=[('email', 'Email')])
    email_type = fields.Selection([('SMTP', 'SMTP'), ('IMAP', 'IMAP'), ('POP', 'POP')])
    email_server = fields.Char("Server URL")
    email_port = fields.Integer("Server Port")

    def connect_email(self):
        if self.ttype == 'email':
            if self.email_type == 'SMTP':
                mailserver = smtplib.SMTP(self.email_server, self.email_port)
                mailserver.ehlo()
                mailserver.login(self.security.user, self.security.password)
                return mailserver

        return False
