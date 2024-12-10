# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import formatLang


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    percent_price = fields.Float(
        string="Percentage Price", compute="_compute_percent_price", readonly=False, store=True
    )
    of_percent_price_formula = fields.Char(
        string="Percentage (discount)", help='Discount or amount of discounts.\nEg. "40 + 10.5" equals "46.3"'
    )
    of_brand_ids = fields.Many2many(
        comodel_name="of.product.brand",
        string="Brands",
        help="If set, the rule will apply only to products from these brands, otherwise to all brands.",
    )
    of_categ_ids = fields.Many2many(comodel_name="product.category", string="Product categories")

    @api.depends("of_percent_price_formula")
    def _compute_percent_price(self):
        """Évalue la formule of_percent_price_formula pour remplir le champ percent_price"""
        for line in self:
            price_percent = 100.0
            if line.of_percent_price_formula:
                try:
                    for discount in map(float, line.of_percent_price_formula.replace(",", ".").split("+")):
                        price_percent *= (100 - discount) / 100.0
                except Exception as e:
                    raise UserError(_("Invalid discount formula:\n%s") % line.of_percent_price_formula) from e
            line.percent_price = 100.0 - price_percent

    def _is_applicable_for(self, product, qty_in_product_uom):
        """Override of `_is_applicable_for` in `odoo/addons/product/models/product_pricelist_item.py` to add specific
        management of brands `of_brand_ids` and new M2M `of_categ_ids` for categories.
        """
        self.ensure_one()
        product.ensure_one()
        res = True

        if self.min_quantity and qty_in_product_uom < self.min_quantity:
            res = False

        elif self.applied_on == "2_product_category":
            if product.categ_id.id not in self.of_categ_ids.ids and not any(
                product.categ_id.parent_path.startswith(categ_id.parent_path) for categ_id in self.of_categ_ids
            ):
                res = False
        else:
            is_product_template = product._name == "product.template"
            # Applied on a specific product template/variant
            if is_product_template:
                if self.applied_on == "1_product" and product.id != self.product_tmpl_id.id:
                    res = False
                elif self.applied_on == "0_product_variant" and not (
                    product.product_variant_count == 1 and product.product_variant_id.id == self.product_id.id
                ):
                    # product self acceptable on template if has only one variant
                    res = False
            elif self.applied_on == "1_product" and product.product_tmpl_id.id != self.product_tmpl_id.id:
                res = False
            elif self.applied_on == "0_product_variant" and product.id != self.product_id.id:
                res = False

        if self.of_brand_ids and product.brand_id.id not in self.of_brand_ids.ids and res:
            return False

        return res

    @api.constrains("product_id", "product_tmpl_id", "categ_id")
    def _check_product_consistency(self):
        """Override of `_check_product_consistency` in `odoo/addons/product/models/product_pricelist_item.py` to add
        specific management of brands `of_brand_ids` and new M2M `of_categ_ids` for categories.
        """
        for item in self:
            if item.applied_on == "2_product_category" and not item.categ_id and not item.of_categ_ids:
                raise ValidationError(_("Please specify the category for which this rule should be applied."))
            elif item.applied_on == "1_product" and not item.product_tmpl_id:
                raise ValidationError(_("Please specify the product for which this rule should be applied."))
            elif item.applied_on == "0_product_variant" and not item.product_id:
                raise ValidationError(_("Please specify the product variant for which this rule should be applied."))

    @api.depends(
        "applied_on",
        "categ_id",
        "product_tmpl_id",
        "product_id",
        "compute_price",
        "fixed_price",
        "pricelist_id",
        "percent_price",
        "price_discount",
        "price_surcharge",
    )
    def _compute_name_and_price(self):
        """Override of `_compute_name_and_price` in `odoo/addons/product/models/product_pricelist_item.py` to add
        specific management of brands `of_brand_ids` and new M2M `of_categ_ids` for categories.
        """
        for item in self:
            if (item.categ_id or item.of_categ_ids) and item.applied_on == "2_product_category":
                item.name = _(
                    "Category(ies) : %(categ_names)s",
                    categ_names=item.categ_id.display_name or ", ".join(item.of_categ_ids.mapped("display_name")),
                )
            elif item.product_tmpl_id and item.applied_on == "1_product":
                item.name = _("Product: %(pname)s", pname=item.product_tmpl_id.display_name)
            elif item.product_id and item.applied_on == "0_product_variant":
                item.name = _("Variant: %(pname)s", pname=item.product_id.display_name)
            else:
                item.name = _("All products")

            if item.compute_price == "fixed":
                item.price = formatLang(
                    item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id
                )
            elif item.compute_price == "percentage":
                item.price = _("%(percent)s %% discount", percent=item.percent_price)
            else:
                item.price = _(
                    "%(percentage)s %% discount and %(price)s surcharge",
                    percentage=item.price_discount,
                    price=item.price_surcharge,
                )
