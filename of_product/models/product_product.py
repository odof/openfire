# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price = fields.Float(of_unify_companies=True)
    of_forced_lst_price = fields.Float(string="Sale price (forced)", digits="Product Price")

    # ---------------------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------------------

    @api.depends("list_price", "price_extra", "of_forced_lst_price")
    @api.depends_context("uom")
    def _compute_product_lst_price(self):
        if not self.env.user.has_group("of_product.group_product_variant_specific_price"):
            return super()._compute_product_lst_price()

        to_uom = None
        if "uom" in self._context:
            to_uom = self.env["uom.uom"].browse(self._context["uom"])

        for product in self:
            list_price = product.of_forced_lst_price or product.list_price
            if to_uom:
                list_price = product.uom_id._compute_price(list_price, to_uom)
            product.lst_price = list_price

    @api.onchange("lst_price")
    def _set_product_lst_price(self):
        if not self.env.user.has_group("of_product.group_product_variant_specific_price"):
            return super()._set_product_lst_price()
        for product in self:
            if self._context.get("uom"):
                value = (
                    self.env["uom.uom"].browse(self._context["uom"])._compute_price(product.lst_price, product.uom_id)
                )
            else:
                value = product.lst_price
            product.write({"of_forced_lst_price": value})

    # ---------------------------------------------------------------------------
    # CRUD methods
    # ---------------------------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == "of_unify_companies" or super()._valid_field_parameter(field, name)

    # ---------------------------------------------------------------------------
    # Business methods
    # ---------------------------------------------------------------------------

    def price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        if self.env.user.has_group("of_product.group_product_variant_specific_price"):
            return super().price_compute("lst_price", uom=uom, currency=currency, company=company, date=date)
        return super().price_compute(price_type, uom=uom, currency=currency, company=company, date=date)

    @api.model
    def _add_missing_default_values(self, values):
        # Mettre la référence produit (default_code) du template par défaut lors de la création d'une variante.
        if "product_tmpl_id" in values and values["product_tmpl_id"]:
            values["default_code"] = self.env["product.template"].browse(values["product_tmpl_id"]).default_code
        return super(ProductProduct, self)._add_missing_default_values(values)
