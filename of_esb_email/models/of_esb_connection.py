# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import smtplib

from odoo import fields, models


class ESBConnection(models.Model):
    _inherit = "of.esb.connection"

    ttype = fields.Selection(selection_add=[("email", "Email")])
    email_type = fields.Selection(selection=[("SMTP", "SMTP"), ("IMAP", "IMAP"), ("POP", "POP")])
    email_server = fields.Char(string="Server URL")
    email_port = fields.Integer(string="Server Port")

    def connect_email(self):
        if self.ttype == "email":
            if self.email_type == "SMTP":
                mailserver = smtplib.SMTP(self.email_server, self.email_port, timeout=10)
                mailserver.ehlo()
                mailserver.login(self.security.user, self.security.password)
                return mailserver
            if self.email_type == "IMAP":
                pass  # only SMTP is supported for now
            if self.email_type == "POP":
                pass  # only SMTP is supported for now
        return False
