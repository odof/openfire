# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFImportProductCategConfig(models.Model):
    _inherit = "of.import.product.categ.config"

    is_datastore_matched = fields.Boolean(string="Is centralized")
