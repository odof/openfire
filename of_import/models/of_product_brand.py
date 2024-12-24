# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from .of_import_error import OfImportError
from .utils import compute_discount


class OFProductBrand(models.Model):
    _name = "of.product.brand"
    _inherit = ["of.product.brand", "of.import.product.config.template"]

    categ_ids = fields.One2many(
        comodel_name="of.import.product.categ.config", inverse_name="brand_id", string="Categories"
    )
    product_config_ids = fields.One2many(
        comodel_name="product.template",
        string="Products",
        compute="_compute_product_config_ids",
        inverse="_inverse_product_config_ids",
        domain="[('brand_id', '=', id)]",
    )

    of_import_sale_price = fields.Char(required=True, default="ppht", string="Sale Price")
    of_import_cost_price = fields.Char(required=True, default="pa", string="Cost Price")
    of_import_categ_id = fields.Many2one(comodel_name="product.category", required=True, string="Category")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("product_ids.of_import_sale_price", "product_ids.of_import_discount", "product_ids.of_import_categ_id")
    def _compute_product_config_ids(self):
        product_obj = self.env["product.template"]
        fields_list = self._get_config_field_list()
        domain = ["|"] * (len(fields_list) - 1) + [(field, "!=", False) for field in fields_list]
        for brand in self:
            brand.product_config_ids = product_obj.search([("brand_id", "=", brand.id)] + domain)

    # -------------------------------------------------------------------------
    # Inverse methods
    # -------------------------------------------------------------------------

    def _inverse_product_config_ids(self):
        # This inverse function is here to allow the modification of the O2M
        pass

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        if vals.get("product_config_ids"):
            product_obj = self.env["product.template"]
            fields_list = self._get_config_field_list()
            deleted_product_ids = []
            for line in vals["product_config_ids"]:
                # For the value "line[0] == 4" no modification allowed here and we don't want to update the Product.
                # For the value "line[0] == 0" we will do nothing because we are assuming that nobody would create
                # a Product here.
                if line[0] in (Command.DELETE, Command.UNLINK):
                    # Suppression de ligne = annulation des règles de calcul
                    deleted_product_ids.append(line[1])
                if line[0] == Command.UPDATE:
                    # Ajout ou modification d'une ligne = définition des règles de calcul
                    product_obj.browse(line[1]).write(
                        {field: line[2][field] for field in fields_list if field in line[2]}
                    )
            if deleted_product_ids:
                product_obj.browse(deleted_product_ids).write(dict.fromkeys(fields_list, False))
        return res

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_update_products(self):
        """Recalculates item fields according to brand configuration and item import parameters
        (in product_supplierinfo)"""
        self.mapped("product_ids").action_button_update_from_brand()

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def compute_product_categ(self, categ_name, product=None):
        """
        Compute the product category based on the given category name and product.

        :param categ_name: The name of the category.
        :param product: The product for which the category is being computed.
        :return: The computed product category.
        """
        self.ensure_one()

        # Configuration de la catégorie au niveau de l'article
        if product and product.of_import_categ_id:
            return product.of_import_categ_id

        # Configuration de la catégorie dans la marque pour ce nom de catégorie fournisseur
        categ_config = self.env["of.import.product.categ.config"].search(
            [("brand_id", "=", self.id), ("categ_origin", "=", categ_name)]
        )
        if categ_config and categ_config.of_import_categ_id:
            return categ_config.of_import_categ_id

        # Enfin, dernière solution, retour de la catégorie par défaut pour la marque
        return self.of_import_categ_id

    def compute_product_price(
        self,
        public_price_untaxed,
        categ_name,
        uom,
        uom_po,
        product=None,
        price=None,
        discount=None,
        cost=None,
        based_on_price=False,
        other_vals=None,
    ):
        """
        Compute the product price based on the given parameters.

        :param public_price_untaxed: The public price excluding taxes.
        :param categ_name: The name of the product category as provided by the supplier.
        :param uom: The unit of measure for the product.
        :param uom_po: The unit of measure used for purchases.
        :param product: The existing product template object in the database.
        :param price: The purchase price that can be used if no formula is specified for the discount.
        :param discount: The discount percentage to be applied.
        :param cost: The cost of the product.
        :param based_on_price: Flag indicating whether the sale price is based on the purchase price.
        :param other_vals: Additional values to be considered.

        :return: A dictionary containing the computed values for various price fields.
        """
        self.ensure_one()
        if not other_vals:
            other_vals = {}

        categ_config = self.env["of.import.product.categ.config"].search(
            [("brand_id", "=", self.id), ("categ_origin", "=", categ_name)]
        )

        udm_ratio = uom_po._compute_price(1.0, uom) if uom_po else 1.0
        eval_dict = self._get_eval_dict(public_price_untaxed, price, cost, other_vals, product, udm_ratio)

        price_fields = self._get_price_fields()
        if (
            not product
            or product.id < 0
            or product.cost_method == "standard"
            or product.categ_id.of_import_update_standard_price
        ):
            # Do not calculate the cost for items that use real cost or average cost
            price_fields.append(("of_import_cost_price", "standard_price", _("Cost Price")))

        values = self._calculate_price_fields(
            price_fields, product, categ_config, eval_dict, public_price_untaxed, price, discount, based_on_price
        )
        values["of_seller_pp_untaxed"] = eval_dict["ppht"]
        values["of_seller_price"] = eval_dict["pa"]
        if "list_price" in values:
            values["list_price"] *= udm_ratio
        if "standard_price" in values:
            values["standard_price"] *= udm_ratio
        if "of_theoretical_cost" in values:
            values["of_theoretical_cost"] *= udm_ratio
        return values

    def compute_product_values(
        self,
        public_price_untaxed,
        categ_name,
        uom_id,
        uom_po_id,
        product=None,
        price=None,
        discount=None,
        cost=None,
        based_on_price=False,
    ):
        """Compute the values for a product based on the given parameters.

        :param public_price_untaxed: The public price excluding taxes.
        :param categ_name: The name of the product category.
        :param uom_id: The ID of the unit of measure.
        :param uom_po_id: The ID of the purchase unit of measure.
        :param product: The product object.
        :param price: The product price.
        :param discount: The product discount.
        :param cost: The product cost.
        :param based_on_price: Flag indicating whether the computation is based on price (default to False).
        :return: A dictionary containing the computed values.
        :raises UserError: If the corresponding product category cannot be found.
        """
        self.ensure_one()

        categ = self.compute_product_categ(categ_name, product=product)
        if not categ:
            raise UserError(_("Unable to find the corresponding product category for %s") % categ_name)

        values = self.compute_product_price(
            public_price_untaxed,
            categ_name,
            uom_id,
            uom_po_id,
            product=product,
            price=price,
            discount=discount,
            cost=cost,
            based_on_price=based_on_price,
        )
        values["categ_id"] = categ.id
        return values

    def _calculate_price_fields(
        self, price_fields, product, categ_config, eval_dict, public_price_untaxed, price, discount, based_on_price
    ):
        """Calculate the values for the given price fields based on the provided parameters.

        :param price_fields: The list of price fields to be calculated.
        :param product: The product object.
        :param categ_config: The category configuration object.
        :param eval_dict: The evaluation dictionary.
        :param public_price_untaxed: The public price.
        :param price: The price.
        :param discount: The discount.
        :param based_on_price: Flag indicating whether the sale price is based on the purchase price.
        :return: A dictionary containing the calculated values for the price fields.
        :raises OfImportError: If no formula is provided for a price field.
        """
        values = {}
        for config_field, product_field, text in price_fields:
            for obj in (product, categ_config, self):
                if obj and obj[config_field]:
                    if product_field == "list_price" and obj[config_field].strip() == "pv":
                        # Do nothing, keep the sale price unchanged
                        break
                    value = safe_eval(obj[config_field], eval_dict)
                    if product_field == "discount":
                        if based_on_price:
                            # Sale price based on the purchase price
                            if not price:
                                # During an import, there is often only one column for both values
                                # The sale price becomes the purchase price
                                eval_dict["pa"] = public_price_untaxed
                                price = public_price_untaxed
                            eval_dict["ppht"] = price * 100.0 / (100.0 - value)
                        else:
                            # Once the discount is calculated, add the purchase price to eval_dict
                            # for the calculation of the final cost
                            eval_dict["pa"] = public_price_untaxed * (100.0 - value) / 100.0
                    else:
                        values[product_field] = value
                    break
            else:  # no break occurred
                if product_field != "discount":
                    raise OfImportError(
                        _(
                            "No formula is provided for %(text)s of this item (brand to be configured: %(name)s)..",
                            text=text,
                            name=self.name,
                        )
                    )

                # If the discount formula is not specified, keep the original purchase price
                if price is not None:
                    # The price is specified at the import level
                    eval_dict["pa"] = price
                elif discount is not None:
                    # The discount is specified at the import level
                    if based_on_price:
                        # Sale price based on the purchase price
                        eval_dict["ppht"] = price * 100.0 / (100.0 - discount)
                    else:
                        # Once the discount is calculated, add the purchase price to eval_dict
                        # for the calculation of the final cost
                        eval_dict["pa"] = public_price_untaxed * (100.0 - discount) / 100.0
                elif product:
                    # The item already exists, keep its purchase price
                    eval_dict["pa"] = product.of_seller_price
                else:
                    # The formula is not specified and no value can be deduced
                    raise OfImportError(
                        _(
                            "No formula is provided for %(text)s of this item (brand to configure: %(name)s)..",
                            text=text,
                            name=self.name,
                        )
                    )
        return values

    def _get_price_fields(self):
        """Get the list of price fields to be calculated."""
        return [
            ("of_import_discount", "discount", _("Discount")),
            ("of_import_sale_price", "list_price", _("Selling price excluding taxes")),
            ("of_import_cost_price", "of_theoretical_cost", _("Theoretical cost")),
        ]

    def _get_eval_dict(self, public_price_untaxed, price, cost, other_vals, product, udm_ratio):
        """Get the evaluation dictionary for the given parameters.
        Watch out if you change keys, you must also change the keys in formulas, help of fields and in the views.
        They are also used to explain the user what he can use in the formulas.
        """
        return {
            "ppht": public_price_untaxed,
            "pa": price,
            "pr": cost,
            "cumul": compute_discount,
            "udm_ratio": udm_ratio,
            # Pricing structure
            "tr_a": other_vals.get("of_purchase_transport", product and product.of_purchase_transport or 0),
            "tr_v": other_vals.get("of_sale_transport", product and product.of_sale_transport or 0),
            "coef": other_vals.get("of_sale_coeff", product and product.of_sale_coeff or 0),
            "fr_l": other_vals.get("of_other_logistic_costs", product and product.of_other_logistic_costs or 0),
            "taxe": other_vals.get("of_misc_taxes", product and product.of_misc_taxes or 0),
            "fr_d": other_vals.get("of_misc_costs", product and product.of_misc_costs or 0),
        }
