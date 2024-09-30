# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFProductStandard(models.Model):
    _name = "of.product.standard"
    _description = "Product standard"
    _rec_name = "code"
    _order = "code"

    code = fields.Char(required=True)
    name = fields.Char(translate=True)
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)
    display_docs = fields.Boolean(string="Display in documents", default=True)
    product_ids = fields.One2many(comodel_name="product.template", inverse_name="of_standard_id", string="Products")

    def write(self, vals):
        prods_to_update = self.env["product.template"]
        if "description" in vals:
            # On met à jour la description de norme des produits si celle-ci n'a pas été personnalisée
            # (valeur identique à la description de la norme)
            for standard in self:
                prods_to_update += standard.product_ids.filtered(
                    lambda p: p.of_standard_description == standard.description
                )
        result = super().write(vals)
        if prods_to_update:
            prods_to_update.write({"of_standard_description": vals["description"]})
        return result
