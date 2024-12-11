# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResUsers(models.Model):
    _name = "res.users"
    _inherit = ["res.users", "of.datastore.model"]
