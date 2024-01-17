# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class OFServiceRequestLine(models.Model):
    _name = 'of.service.request.line'
    _description = "Service Request Line"

    # General
    request_id = fields.Many2one(
        comodel_name='of.service.request', string="Service Request", required=True, ondelete='cascade'
    )
    order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string="Sale Order Line",
        help="Used to find out whether a order has been generated for this line.",
    )
    so_number = fields.Char(string="Sale Order Number", related='order_line_id.order_id.name', readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', related='request_id.partner_id', readonly=True)
    company_id = fields.Many2one(
        comodel_name='res.company', related='request_id.company_id', string="Company", readonly=True
    )

    # Product
    product_id = fields.Many2one(comodel_name='product.product', string="Product")
    qty = fields.Float(digits='Product Unit of Measure', default=1.0)
    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True,
        readonly=False,
    )

    # Currency & Pricing
    currency_id = fields.Many2one(
        comodel_name='res.currency', string="Currency", readonly=True, related='company_id.currency_id'
    )
    price_unit = fields.Float(
        digits='Product Price',
        default=0.0,
        compute='_compute_price_unit',
        store=True,
        readonly=False,
    )
    price_subtotal = fields.Monetary(compute='_compute_amount', string="Subtotal", readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string="Taxes", readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string="Total", readonly=True, store=True)
    discount = fields.Float(string="Discount (%)", digits='Discount', default=0.0)
    tax_ids = fields.Many2many(
        comodel_name='account.tax', string="VAT", compute='_compute_tax_ids', store=True, readonly=False
    )

    # Invoicing
    invoice_status = fields.Selection(
        selection=[
            ('no', "Nothing to Bill"),
            ('to invoice', "Waiting Bills"),
            ('invoiced', "Fully Billed"),
        ],
        string="Billing Status",
        compute='_compute_invoice_status',
        store=True,
    )
    qty_invoiced = fields.Float(string="Invoiced qty", compute='_compute_qty_invoiced', store=True)
    qty_invoiceable = fields.Float(string="Invoiceable qty", compute='_compute_qty_invoiceable', store=True)
    invoice_line_ids = fields.One2many(
        comodel_name='account.move.line', inverse_name='of_request_line_id', string="Invoice Line"
    )

    # -----------------------------------------------------------------------
    # Compute methods
    # -----------------------------------------------------------------------

    @api.depends('qty', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        for line in self:
            company = line.request_id.company_id

            # Rounding is the default setting
            with_round = not company or company.tax_calculation_rounding_method != 'round_globally'
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.with_context(round=with_round).compute_all(
                price, line.currency_id, line.qty, product=line.product_id, partner=line.request_id.address_id
            )
            if not with_round:
                # Truncation is used here, as the "update" automatically rounds up.
                taxes['total_included'] = int(taxes['total_included'] * 100) / 100.0
            line.update(
                {
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                }
            )

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self.filtered(lambda li: li.product_id):
            line.price_unit = line.product_id.lst_price

    @api.depends('product_id')
    def _compute_name(self):
        for line in self.filtered(lambda li: li.product_id):
            name = line.product_id.name_get()[0][1]
            if line.product_id.description_sale:
                name += '\n' + line.product_id.description_sale
            line.name = name

    @api.depends('product_id', 'company_id', 'partner_id')
    def _compute_tax_ids(self):
        for line in self:
            fiscal_position = line.request_id.fiscal_position_id
            taxes = line.company_id._of_filter_taxes(line.product_id.taxes_id)
            line.tax_ids = fiscal_position and fiscal_position.map_tax(taxes) or taxes

    @api.depends('invoice_line_ids', 'invoice_line_ids.move_id', 'invoice_line_ids.quantity')
    def _compute_qty_invoiced(self):
        for line in self:
            line.qty_invoiced = sum(line.mapped('invoice_line_ids.quantity'))

    @api.depends('qty', 'qty_invoiced', 'order_line_id')
    def _compute_qty_invoiceable(self):
        for line in self:
            if line.order_line_id:
                line.qty_invoiceable = 0.0
            else:
                line.qty_invoiceable = line.qty - line.qty_invoiced

    @api.depends('qty', 'qty_invoiced', 'order_line_id', 'qty_invoiceable')
    def _compute_invoice_status(self):
        for line in self:
            if line.order_line_id:
                line.invoice_status = 'no'

    # -----------------------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------------------

    def _prepare_intervention_line_vals(self):
        self.ensure_one()
        res = {
            'product_id': self.product_id and self.product_id.id or False,
            'price_unit': self.price_unit,
            'qty': self.qty,
            'name': self.name,
            'discount': self.discount,
            'order_line_id': self.order_line_id and self.order_line_id.id or False,
        }
        if self.tax_ids:
            res['tax_ids'] = [Command.set(self.tax_ids.ids)]
        return res

    def _prepare_so_line_vals(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty,
            'of_request_line_id': self.id,
        }
