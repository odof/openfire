# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    of_copy_to_sender = fields.Boolean(string="E-mail copy to sender")

    def create_action(self):
        return super(MailTemplate, self.sudo()).create_action()

    def unlink_action(self):
        return super(MailTemplate, self.sudo()).unlink_action()
