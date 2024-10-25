# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from .tools import _get_list_from_parameter


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_is_poujoulat_product = fields.Boolean(compute="_compute_of_is_poujoulat_product", store=True)
    of_poujoulat_artas400 = fields.Char(string="Artas400")
    of_poujoulat_variant = fields.Integer(string="Item variant")
    of_poujoulat_cond_unit = fields.Char(string="Conditioning unit")

    @api.depends("brand_id")
    def _compute_of_is_poujoulat_product(self):
        """
        Sets 'of_is_poujoulat_product' to True if the product's brand is in the configured Poujoulat brand IDs.
        """
        brand_ids = _get_list_from_parameter(self, "of.connector.poujoulat.brand_ids")
        filtered_produdcts = self.filtered(lambda p: p.brand_id and p.brand_id.id in brand_ids)
        for record in filtered_produdcts:
            record.of_is_poujoulat_product = True
        for record in self - filtered_produdcts:
            record.of_is_poujoulat_product = False
