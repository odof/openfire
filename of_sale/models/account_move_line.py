# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _order = "date desc, move_name desc, of_order_id, id"

    price_unit = fields.Float(digits=False)
    of_is_locked = fields.Boolean(
        compute="_compute_of_is_locked",
        string="Locked",
        help="Special product. That field allows you to know if an invoice line should prevent its counterpart on a "
        "sale order from being deleted",
    )
    of_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Origin Customer Order",
    )

    @api.model
    def _get_locked_category_ids(self):
        """For inheritance purpose. Get the ids of the categories that are locked."""
        ids = []
        ir_config_param_obj = self.env["ir.config_parameter"].sudo()
        if deposit_categ_id := ir_config_param_obj.get_param("of.sale.of_deposit_product_categ_id"):
            ids.append(int(deposit_categ_id))  # M2O field in res.config.settings
        return ids

    @api.model
    def _get_locked_product_ids(self):
        """For inheritance purpose. Get the ids of the products that are locked."""
        ids = []
        ir_config_param_obj = self.env["ir.config_parameter"].sudo()
        if deposit_product_id := ir_config_param_obj.get_param("sale.default_deposit_product_id"):
            ids.append(int(deposit_product_id))  # M2O field in res.config.settings
        return ids

    @api.depends("product_id")
    def _compute_of_is_locked(self):
        """Compute the value of of_is_locked field.
        `of_is_locked` is a field that allows us to know if an invoice line should prevent its counterpart on a
        sale order from being deleted (see `sale.order.line.unlink()`)
        """
        locked_category_ids = self._get_locked_category_ids()
        locked_product_ids = self._get_locked_product_ids()
        for invoice_line in self:
            invoice_line.of_is_locked = (
                invoice_line.product_id.categ_id.id in locked_category_ids
                or invoice_line.product_id.id in locked_product_ids
            )

    @api.depends("product_id", "journal_id")
    def _compute_name(self):
        super()._compute_name()
        show_manufacturer_description = self.env.user.company_id.show_manufacturer_description in (
            "invoices",
            "both",
        )
        for line in self:
            product = line.product_id.with_context(
                lang=line.move_id.partner_id.lang,
                partner=line.move_id.partner_id.id,
            )
            if show_manufacturer_description and product and product.of_manufacturer_description:
                line.name += "\n" + product.of_manufacturer_description

    def write(self, vals):
        res = super().write(vals)
        res and self._sync_sale_order_line_fields(vals)
        return res

    def _sync_sale_order_line_fields(self, vals):
        """Synchronize the fields of the account move line with the sale order line for all locked lines."""
        # Fields to synchronize between the account move line and the sale order line
        # (key: account.move.line field, value: sale.order.line field)
        fields_to_sync_mapping = self._get_fields_sync_mapping()
        fields_to_sync = [x for x in fields_to_sync_mapping if x in vals.keys()]
        vals_order_line = {fields_to_sync_mapping[field]: vals[field] for field in fields_to_sync}
        for line in self.filtered("of_is_locked"):
            if (
                line.move_id.invoice_line_ids.filtered("of_is_locked") == line.move_id.invoice_line_ids
                and len(line.sale_line_ids) == 1
                and line.sale_line_ids.invoice_lines == line
            ):
                line.sale_line_ids.with_context(
                    force_price=True, of_force_protected_fields=list(fields_to_sync_mapping.values())
                ).write(vals_order_line)

    def _get_fields_sync_mapping(self):
        """For inheritance purpose. Get the mapping between the fields of the account move line and the
        sale order line"""
        return {
            "price_unit": "price_unit",
            "product_uom_id": "product_uom",
            "discount": "discount",
            "tax_ids": "tax_id",
        }
