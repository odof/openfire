# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class IrBinary(models.AbstractModel):
    _name = "ir.binary"
    _inherit = ["ir.binary", "of.datastore.model"]
