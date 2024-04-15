# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFEquipment(models.Model):
    _name = "of.equipment"
    _inherit = ["of.equipment", "of.datastore.product.reference"]
