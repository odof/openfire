# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # if both `of_datastore_supplier` and `of_datastore_product` are installed, we want these fields not to be readonly
    of_prochain_tarif = fields.Float(readonly=False)
    of_date_prochain_tarif = fields.Date(readonly=False)
