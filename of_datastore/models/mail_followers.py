# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailMessage(models.Model):
    _name = "mail.message"
    _inherit = ["mail.message", "of.datastore.model"]
