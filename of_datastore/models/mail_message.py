# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailFollowers(models.Model):
    _name = "mail.followers"
    _inherit = ["mail.followers", "of.datastore.model"]
