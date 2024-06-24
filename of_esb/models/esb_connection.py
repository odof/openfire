# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import smtplib

from odoo import fields, models


class ESBConnection(models.Model):
    _name = 'esb.connection'

    name = fields.Char()
    ttype = fields.Selection([('email', 'Email')], default='email', string="Type")
    email_type = fields.Selection([('SMTP', 'SMTP'), ('IMAP', 'IMAP'), ('POP', 'POP')])
    email_server = fields.Char("Server URL")
    email_port = fields.Integer("Server Port")
    security = fields.Many2one(comodel_name='esb.security', string="Security")

    def connect(self):
        if self.ttype == 'email':
            if self.email_type == 'SMTP':
                mailserver = smtplib.SMTP(self.email_server, self.email_port)
                mailserver.ehlo()
                mailserver.login(self.security.user, self.security.password)
                return mailserver

        return False
