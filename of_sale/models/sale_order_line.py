# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.models import regex_order
from odoo.tools import float_compare, float_is_zero, get_lang


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "of.readgroup", "of.form.readonly"]

    price_unit = fields.Float(  # Override to add help text
        help="Unit price of the article. To enter without VAT or with VAT according to the order line.",
    )

    # Compute fields
    of_main_product = fields.Boolean(
        string="Main product",
        help="This line is the main product of the order",
        compute="_compute_of_main_product",
        store=True,
        readonly=False,
        precompute=True,
    )
    of_invoice_policy = fields.Selection(
        selection=[("order", "Ordered quantities"), ("delivery", "Delivered quantities")],
        string="Invoicing policy",
        compute="_compute_of_invoice_policy",
        store=True,
        precompute=True,
    )
    of_estimated_invoicing_date = fields.Date(
        string="Estimated invoicing date",
        compute="_compute_of_estimated_invoicing_date",
        store=True,
        compute_sudo=True,
        precompute=True,
    )
    of_gb_partner_tag_id = fields.Many2one(
        comodel_name="res.partner.category",
        compute=lambda *a, **k: {},
        search="_search_of_gb_partner_tag_id",
        string="Partner tag",
        of_custom_groupby=True,
    )
    of_price_unit_taxexcl = fields.Float(
        string="Unit Price Tax excl",
        compute="_compute_of_price_unit",
        digits="Product Price",
        store=True,
        help="Unit price without taxes",
    )
    of_price_unit_taxinc = fields.Float(
        string="Unit Price Tax incl",
        compute="_compute_of_price_unit",
        digits="Product Price",
        store=True,
        help="Unit price with taxes",
    )

    # Helper, related fields
    of_product_categ_id = fields.Many2one(
        comodel_name="product.category", related="product_id.categ_id", store=True, index=True
    )
    of_product_default_code = fields.Char(related="product_id.default_code", string="Product Reference", readonly=True)
    of_price_date_display = fields.Char(compute="_compute_of_price_date_display", string="Price date")
    of_obsolete = fields.Boolean(string="Obsolete Product", related="product_id.of_obsolete", readonly=True)
    date_order = fields.Datetime(related="order_id.date_order", store=True, index=True)
    of_customer_view = fields.Boolean(string="Customer/Vendor view", related="order_id.of_customer_view")
    of_order_partner_shipping_id = fields.Many2one(related="order_id.partner_shipping_id")
    of_client_order_ref = fields.Char(related="order_id.client_order_ref")
    of_commitment_date = fields.Datetime(related="order_id.commitment_date")

    # Related fields for the sale order line custom form view called by `action_button_open_sale_order_line`
    of_order_state = fields.Selection(
        related="order_id.state",
        string="Order State",
        readonly=True,
    )
    of_order_company_id = fields.Many2one(
        related="order_id.company_id",
        string="Order Company",
        readonly=True,
    )
    of_order_partner_id = fields.Many2one(
        related="order_id.partner_id",
        string="Order Customer",
        readonly=True,
    )
    of_order_pricelist_id = fields.Many2one(
        related="order_id.pricelist_id",
        string="Pricelist",
        readonly=True,
    )
    of_order_tax_country_id = fields.Many2one(
        related="order_id.tax_country_id",
        string="Tax Country",
        readonly=True,
    )

    # ---------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------

    @api.model
    def _search_of_gb_partner_tag_id(self, operator, value):
        return [("order_partner_id.category_id", operator, value)]

    @api.depends(
        "product_id",
        "product_id.invoice_policy",
        "order_id",
        "order_id.of_invoice_policy",
        "order_partner_id",
        "order_partner_id.of_invoice_policy",
    )
    def _compute_of_invoice_policy(self):
        for line in self:
            line.of_invoice_policy = (
                line.order_id.of_invoice_policy
                or line.order_partner_id.of_invoice_policy
                or line.product_id.invoice_policy
                or self.env["ir.default"].get("product.template", "invoice_policy")
            )

    # no trigger product_id.invoice_policy to avoid retroactively changing SO
    @api.depends("qty_invoiced", "qty_delivered", "product_uom_qty", "state", "of_invoice_policy")
    def _compute_qty_to_invoice(self):
        """Overridden to take into account the custom invoice policy"""
        for line in self:
            if line.state in ["sale", "done"] and not line.display_type:
                if line.of_invoice_policy == "order":
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:  # invoice_policy == 'delivery'
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.depends(
        "of_invoice_policy",
        "order_id",
        "order_id.of_fixed_invoice_date",
        "move_ids",
    )
    def _compute_of_estimated_invoicing_date(self):
        for line in self:
            if line.of_invoice_policy == "delivery":
                if moves := line.mapped("move_ids").sorted("date"):
                    line.of_estimated_invoicing_date = fields.Date.to_date(moves[0].date)
            elif line.of_invoice_policy == "order":
                line.of_estimated_invoicing_date = line.order_id.of_estimated_invoicing_date

    @api.depends("product_id")
    def _compute_of_main_product(self):
        for line in self:
            if line.product_id and line.product_id.categ_id:
                line.of_main_product = line.product_id.categ_id.of_main_product

    @api.depends(
        "state",
        "product_uom_qty",
        "qty_delivered",
        "qty_to_invoice",
        "qty_invoiced",
        "order_id.of_force_invoice_status",
    )
    def _compute_invoice_status(self):
        """This method is a copy of the original method `_compute_invoice_status` from `sale_order_line.py`.
        The only difference is that we added the line `line.order_id.of_force_invoice_status` in
        the `if/elif` statement at the beginning of the method.
        """
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for line in self:
            if line.order_id.of_force_invoice_status:
                line.invoice_status = line.order_id.of_force_invoice_status
            elif line.state not in ("sale", "done"):
                line.invoice_status = "no"
            elif line.is_downpayment and line.untaxed_amount_to_invoice == 0:
                line.invoice_status = "invoiced"
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = "to invoice"
            elif (
                line.state == "sale"
                and line.product_id.invoice_policy == "order"
                and line.product_uom_qty >= 0.0
                and float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1
            ):
                line.invoice_status = "upselling"
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = "invoiced"
            else:
                line.invoice_status = "no"

    def _compute_of_price_date_display(self):
        for line in self:
            msg_date = (
                line.product_id.of_cost_date.strftime(get_lang(self.env).date_format)
                if line.product_id.of_cost_date
                else False
            )
            line.of_price_date_display = f"({msg_date})" if msg_date else _("(Undated)")

    @api.depends("product_id")
    def _compute_name(self):
        self = self.with_context(display_default_code=False)
        super()._compute_name()
        show_manufacturer_description = self.env.user.company_id.show_manufacturer_description in (
            "sales",
            "both",
        )
        for line in self:
            product = line.product_id.with_context(
                lang=line.order_id.partner_id.lang,
                partner=line.order_id.partner_id.id,
            )
            if show_manufacturer_description and product and product.of_manufacturer_description:
                line.name += "\n" + product.of_manufacturer_description

    @api.depends("product_id")
    def _compute_tax_id(self):
        """Override to avoid computing taxes on SO lines when the product is tag as locked"""
        if self._context.get("of_from_deposit_wizard"):
            # We want to compute taxes on SO lines when creating a deposit from the wizard
            return super()._compute_tax_id()
        return super(
            SaleOrderLine, self.filtered(lambda line: not line._additionnal_tax_verifications())
        )._compute_tax_id()

    @api.depends("price_unit", "product_id", "tax_id", "currency_id", "order_id.partner_shipping_id")
    def _compute_of_price_unit(self):
        for line in self:
            prices = line.tax_id.compute_all(
                line.price_unit,
                currency=line.currency_id,
                quantity=1,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id,
            )
            line.of_price_unit_taxexcl = prices["total_excluded"]
            line.of_price_unit_taxinc = prices["total_included"]

    # ---------------------------------------------------------
    # ORM methods
    # ---------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == "of_custom_groupby" or super()._valid_field_parameter(field, name)

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        if self.env.user.has_group("of_sale.of_group_restrict_form_sale_order_modification") and view_type == "form":
            self = self.with_context(form_readonly="[('of_order_state', '=', 'sale')]")
        return super()._get_view(view_id=view_id, view_type=view_type, **options)

    def write(self, vals):
        blocked = [x for x in self._get_blocked_fields_on_write() if x in vals.keys()]
        for line in self:
            locked_invoice_lines = line.mapped("invoice_lines").filtered(lambda line: line.of_is_locked)
            if locked_invoice_lines and blocked and not self._context.get("force_price"):
                raise UserError(_("This line cannot be modified: %s") % line.name)
        return super().write(vals)

    def _write(self, vals):
        for field in vals:
            if field != "of_product_categ_id":
                break
        else:  # No other field than of_product_categ_id
            # We need to sudo to avoid access rights issues when writing on the category of the product on the SO line
            # where the user has no access rights to this sale order line. (`of_product_categ_id` is a stored related
            # field)
            self = self.sudo()
        return super(SaleOrderLine, self)._write(vals)

    def unlink(self):
        """Disallow deletion of sale order lines if the line is already present on an invoice that is not a cancelled
        invoice and that has never been validated.
        """
        if self.mapped("invoice_lines").filtered(lambda line: line.move_id.state != "cancel" or line.move_name != "/"):
            raise UserError(_("You cannot delete an item line linked to an invoice.\nPlease cancel your changes."))
        return super().unlink()

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """Override to add the possibility to group by customer tag"""
        if gb != "of_gb_partner_tag_id":
            return super()._read_group_process_groupby(gb, query)

        split = gb.split(":")
        field = self._fields.get(split[0])
        if not field:
            raise ValueError("Invalid field %r on model %r" % (split[0], self._name))
        field_type = field.type
        alias = query.left_join(
            self._table, "order_partner_id", "res_partner_res_partner_category_rel", "partner_id", "category_id"
        )
        return {
            "field": gb,
            "groupby": gb,
            "type": field_type,
            "display_format": None,
            "interval": None,
            "granularity": None,
            "tz_convert": False,
            "qualified_field": f'"{alias}".category_id',
        }

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, reverse_direction, seen):
        if order_field == "of_gb_partner_tag_id":
            dest_model = self.env["res.partner.category"]
            m2o_order = dest_model._order
            if not regex_order.match(m2o_order):
                # _order is complex, can't use it here, so we default to _rec_name
                m2o_order = dest_model._rec_name
            rel_alias = query.left_join(
                alias, "order_partner_id", "res_partner_res_partner_category_rel", "partner_id", "partner_category_rel"
            )
            dest_alias = query.left_join(rel_alias, "category_id", "res_partner_category", "id", "partner_category")
            return dest_model._generate_order_by_inner(dest_alias, m2o_order, query, reverse_direction, seen)
        return []

    # ---------------------------------------------------------
    # Action methods
    # ---------------------------------------------------------

    def action_button_dummy(self):
        pass

    def action_button_open_sale_order_line(self):
        """Open the sale order line in a new window."""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({"of_only_default_code": False})
        form_id = self.env.ref("of_sale.of_sale_order_line_view").id
        return {
            "name": _("Sale Order Line"),
            "view_mode": "form",
            "res_model": "sale.order.line",
            "res_id": self.id,
            "views": [(form_id, "form")],
            "type": "ir.actions.act_window",
            "context": context,
            "target": "new",
        }

    # ---------------------------------------------------------
    # Business logic methods
    # ---------------------------------------------------------

    def _get_blocked_fields_on_write(self):
        """For inheritance purpose. Get the fields that are blocked on write."""
        return ["price_unit", "product_uom_qty", "product_uom", "discount"]

    def _get_protected_fields(self):
        """Override to add the possibility to force the allowed fields given in the context"""
        protected_fields = super()._get_protected_fields()
        if force_allowed_fields := self._context.get("of_force_protected_fields"):
            assert isinstance(
                force_allowed_fields, (list, str)
            ), "of_force_protected_fields must be a list or a string."
            if force_allowed_fields:
                if isinstance(force_allowed_fields, str):
                    force_allowed_fields = [force_allowed_fields]
                for field in force_allowed_fields:
                    protected_fields.remove(field) if field in protected_fields else None
        return protected_fields

    # FIXME ?
    # This method was created from V10 method `product_uom_change` to reuse code in another method
    # The way the price is computed has changed in V16 (see `_compute_price_unit` in
    # odoo/addons/sale/models/sale_order_line.py), so maybe we should use the new method instead
    def of_get_price_unit(self):
        """Returns typical unit price"""
        self.ensure_one()
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get("fiscal_position"),
        )
        return self.env["account.tax"]._fix_tax_included_price_company(
            self._get_display_price(), product.taxes_id, self.tax_id, self.company_id
        )

    def _additionnal_tax_verifications(self):
        """Avoid to compute taxes on SO lines when the product is tag as locked"""
        if not self._origin:  # Creating a new SO line we want to compute taxes
            return False
        move_line_obj = self.env["account.move.line"]
        return (
            True
            if self.product_id and self.product_id.id in move_line_obj._get_locked_product_ids()
            else bool(
                (
                    self.product_id
                    and self.product_id.categ_id
                    and self.product_id.categ_id.id in move_line_obj._get_locked_category_ids()
                )
            )
        )
