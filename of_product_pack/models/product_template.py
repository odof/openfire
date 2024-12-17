# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pack_type = fields.Selection(default="non_detailed", required=True)
    pack_component_price = fields.Selection(selection="_get_pack_component_price", default="totalized", required=True)

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends(lambda self: self._get_pack_modifiable_invisible_depends())
    def _compute_pack_modifiable_invisible(self):
        """Overridden method for computing the pack modifiable invisible field.
        We removed `detailed` value from `pack_component_price` fields.
        """
        for product in self:
            product.pack_modifiable_invisible = product.pack_type != "detailed"

    @api.depends("pack_ok", "pack_component_price", "pack_line_ids", "pack_line_ids.product_id.standard_price")
    def _compute_standard_price(self):
        super()._compute_standard_price()
        for product in self:
            if product.pack_ok and product.pack_component_price == "totalized" and product.pack_line_ids:
                product.standard_price = sum(
                    pack_line.product_id.standard_price * pack_line.quantity for pack_line in product.pack_line_ids
                )
            else:
                product.standard_price = product.standard_price

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)

        # NOTE (improve me): Technical choice to keep updated all Packs using components in pending modification.
        # This context is set only on the O2M components list of a Product pack to keep prices up to date.
        # In that way we are avoiding updating packs during mass product modification (like product imports).
        if self.env.context.get("of_update_product_pack_prices") and any(field in ["list_price"] for field in vals):
            if packs_to_update := (
                (
                    self.env["product.pack.line"]
                    .search(
                        [
                            (
                                "product_id",
                                "in",
                                self.mapped("product_variant_id").ids,
                            )
                        ]
                    )
                    .mapped("parent_product_id")
                )
                .mapped("product_tmpl_id")
                .filtered(lambda pt: pt.pack_component_price == "totalized")
            ):
                packs_to_update.with_context(
                    of_force_pack_totalized_upd=True,
                )._process_list_price()

        # `list_price` is readonly when the product is flagged as pack with a totalize price, so we ensure that is
        # correctly computed during the write.
        if not self.env.context.get("of_pack_avoid_recompute_list_price"):
            self._process_list_price(vals)
        return res

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _process_list_price(self, vals=None):
        if vals is None:
            vals = {}

        if any(field in ["pack_component_price", "pack_line_ids"] for field in vals) or self.env.context.get(
            "of_force_pack_totalized_upd"
        ):
            for product in self.filtered(
                lambda p: p.pack_ok and p.pack_component_price == "totalized" and p.pack_line_ids
            ):
                product.with_context(
                    of_pack_avoid_recompute_list_price=True,
                ).list_price = sum(
                    pack_line.component_price * pack_line.quantity for pack_line in product.pack_line_ids
                )

    def _get_pack_component_price(self):
        """Method for getting the selection for the pack component price."""
        return [
            ("totalized", _("Calculated")),
            ("ignored", _("Fixed")),
        ]

    def _is_pack_to_be_handled(self):
        """Overridden method for getting if a template is a computable pack.

        We change the way `is_pack` is calculated to take into account `non_detailed` packs with `totalized` prices.
        """
        self.ensure_one()
        is_pack = False
        if self.env.context.get("whole_pack_price"):
            # We could need to check the price of the whole pack (e.g.: e-commerce)
            is_pack = self.pack_ok and self.pack_type == "detailed" and self.pack_component_price == "detailed"
        is_pack |= self.pack_ok and (
            (self.pack_type in ["detailed", "non_detailed"] and self.pack_component_price == "totalized")
        )
        return is_pack
