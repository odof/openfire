# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningInterventionLineMixin(models.AbstractModel):
    """
    Mixin class for lines linked to interventions that relate to a product, quantity, price, taxes, etc. and that can be
    invoiced (e.g. `of.planning.intervention.line`, `of.intervention.template.line`,
    `of.equipment.intervention.report.template.line` and of.calendar.event.equipment.link.line`).
    """

    _name = "of.planning.intervention.line.mixin"
    _description = "Intervention line mixin"

    # Company & Partner
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    # Product & Quantity
    name = fields.Text(string="Description", compute="_compute_name", store=True, readonly=False)
    product_id = fields.Many2one(comodel_name="product.product", string="Product", required=True)
    qty = fields.Float(digits="Product Unit of Measure", default=1.0)
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        compute="_compute_uom_id",
        store=True,
        readonly=False,
        precompute=True,
        ondelete="restrict",
    )
    # Pricing
    currency_id = fields.Many2one(
        comodel_name="res.currency", string="Currency", readonly=True, related="company_id.currency_id"
    )
    price_unit = fields.Float(
        string="Unit price",
        digits="Product Price",
        default=0.0,
        compute="_compute_price_unit",
        store=True,
        readonly=False,
    )
    discount = fields.Float(string="Discount (%)", digits="Discount", default=0.0)
    price_subtotal = fields.Monetary(
        compute="_compute_amount", string="Price subtotal", readonly=True, store=True, currency_field="currency_id"
    )
    price_tax = fields.Monetary(
        compute="_compute_amount", string="Taxes", readonly=True, store=True, currency_field="currency_id"
    )
    price_total = fields.Monetary(
        compute="_compute_amount", string="Price total", readonly=True, store=True, currency_field="currency_id"
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax", string="VAT", compute="_compute_tax_ids", store=True, readonly=False
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            if product := line.product_id:
                name = product.name_get()[0][1]
                if product.description_sale:
                    name += "\n" + product.description_sale
                line.name = name
            else:
                line.name = ""

    @api.depends("product_id")
    def _compute_price_unit(self):
        for line in self.filtered(lambda li: li.product_id):
            line.price_unit = line.product_id.lst_price

    @api.depends("product_id")
    def _compute_uom_id(self):
        for line in self:
            if not line.uom_id or (line.product_id.uom_id.id != line.uom_id.id):
                line.uom_id = line.product_id.uom_id

    @api.depends("qty", "price_unit", "tax_ids")
    def _compute_amount(self):
        """
        Compute the amount of the line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                price, line.currency_id, line.qty, product=line.product_id, partner=line._get_partner_taxes()
            )
            line.update(
                {
                    "price_tax": taxes["total_included"] - taxes["total_excluded"],
                    "price_total": taxes["total_included"],
                    "price_subtotal": taxes["total_excluded"],
                }
            )

    @api.depends("product_id", "company_id", "partner_id")
    def _compute_tax_ids(self):
        for line in self:
            fiscal_position = line._get_fiscal_position_taxes()
            taxes = line.company_id._of_filter_taxes(line.product_id.taxes_id)
            line.tax_ids = fiscal_position and fiscal_position.map_tax(taxes) or taxes

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _prepare_intervention_line_vals(self, event):
        self.ensure_one()
        if not event:
            return {}
        return {
            "product_id": self.product_id.id,
            "price_unit": self.price_unit,
            "qty": self.qty,
            "name": self.name,
            "intervention_id": event.id,
        }

    def _get_fiscal_position_taxes(self):
        """
        Get the fiscal position to use for taxes computation.
        This method should be overridden in concrete models.
        """
        self.ensure_one()
        return self.env["account.fiscal.position"].browse()

    def _get_partner_taxes(self):
        """
        Get the partner to use for taxes computation.
        This method should be overridden in concrete models.
        """
        self.ensure_one()
        return self.partner_id
