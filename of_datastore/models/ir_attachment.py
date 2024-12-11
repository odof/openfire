# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IrAttachment(models.Model):
    _name = "ir.attachment"
    _inherit = ["ir.attachment", "of.datastore.model"]
