# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.model
    def _default_product_categ_id(self):
        categ_id = self.env['ir.config_parameter'].sudo().get_param('of.sale.of_deposit_product_categ_id', False)
        categ_id = categ_id and int(categ_id) or False
        return categ_id and self.env['product.category'].browse(categ_id) or self.env['product.category'].browse()

    @api.model
    def _default_product_id(self):
        categ = self._default_product_categ_id()
        products = categ and self.env['product.product'].search([('categ_id', '=', categ.id), ('type', '=', 'service')])
        return len(products) == 1 and products or self.env['product.product'].browse()

    product_categ_id = fields.Many2one(
        comodel_name='product.category',
        string="Down payment items category",
        default=lambda self: self._default_product_categ_id(),
    )
    product_id = fields.Many2one(domain="[('categ_id', '=', product_categ_id), ('type', '=', 'service')]")
    of_nb_products = fields.Integer(compute='_compute_of_nb_products')
    of_include_null_qty_lines = fields.Boolean(string="Include lines in quantity 0 ?")

    @api.depends('product_categ_id')
    def _compute_product_id(self):
        self.product_id = False
        categ = self._default_product_categ_id()
        products = categ and self.env['product.product'].search([('categ_id', '=', categ.id), ('type', '=', 'service')])
        if not products or len(products) > 1:
            return
        for wizard in self:
            if wizard.count == 1:
                wizard.product_id = products.id

    @api.depends('product_categ_id')
    def _compute_of_nb_products(self):
        category = self._default_product_categ_id()
        nb_products = (
            category
            and self.env['product.product'].search(
                [('categ_id', '=', category.id), ('type', '=', 'service')], count=True
            )
            or 0
        )
        for wizard in self:
            wizard.of_nb_products = nb_products

    def _prepare_down_payment_product_values(self):
        self.ensure_one()
        values = super()._prepare_down_payment_product_values()
        values['categ_id'] = self.product_categ_id.id
        return values

    def _prepare_so_line_values(self, order):
        values = super()._prepare_so_line_values(order)
        if so_line_name := self._context.get('of_account_sale_line_name'):
            values['name'] = so_line_name
        return values

    def _prepare_invoice_values(self, order, so_line):
        values = super()._prepare_invoice_values(order, so_line)
        if line_name := self._context.get('of_account_line_name'):
            values['invoice_line_ids'][0][2]['name'] = line_name
        if of_default_deposit_payment_term_id := order.company_id.of_default_deposit_payment_term_id:
            values['invoice_payment_term_id'] = of_default_deposit_payment_term_id.id
        return values

    def _get_down_payment_amount(self, order):
        self.ensure_one()
        # TODO: From OF10, remove me in OF16 ?
        if self.advance_payment_method == 'percentage' and self._context.get('of_tax_included_amount'):
            return order.amount_untaxed * self.amount / 100
        return super()._get_down_payment_amount(order)

    def _create_invoices(self, sale_orders):
        if len(self.sale_order_ids) != 1:  # let the original method do its job when multiple SOs are selected
            return super()._create_invoices(sale_orders)

        # If we asked to create a regular invoice and we already have down payments for this SO, so thats a final
        # invoice
        if self.advance_payment_method == 'delivered' and self.has_down_payments:
            return sale_orders.with_context(of_down_payment_final_invoice=True)._create_invoices(
                final=self.deduct_down_payments
            )
        if self.advance_payment_method in ['percentage', 'fixed']:
            # `advance_payment_method` is available only for one SO, default value is 'delivered'
            # we should have only one SO in here.
            self.sale_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids
            context = {'lang': order.partner_id.lang}  # noqa F841
            of_account_line_name = _("Down payment of %s%%")
            of_account_sale_line_name = _("Advance: %s")
            self = self.with_context(
                of_account_sale_line_name=of_account_sale_line_name % fields.Date.to_string(fields.Date.today()),
            )
            del context
        if self.advance_payment_method == 'percentage' and self._context.get('of_tax_included_amount'):
            # TODO: From OF10, remove me in OF16 ?
            amount = self.amount
            self.amount = amount * order.amount_total / order.amount_untaxed
            self = self.with_context(
                of_account_line_name=of_account_line_name % amount,
            )
        if self.advance_payment_method in ['delivered', 'fixed'] and self.of_include_null_qty_lines:
            self = self.with_context(of_include_null_qty_lines=True)
        return super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)

    def create_invoices(self):
        if self.advance_payment_method in ['percentage', 'fixed'] and not self.env[
            'ir.config_parameter'
        ].sudo().get_param('of.sale.of_deposit_product_categ_id', False):
            self.env['ir.config_parameter'].sudo().set_param(
                'of.sale.of_deposit_product_categ_id', self.product_categ_id.id
            )
        # We want to compute taxes on SO lines when creating a deposit from the wizard.
        # (see the filter in `_compute_tax_id` on `_additionnal_tax_verifications` in of_sale/models/sale.py)
        self = self.with_context(of_from_deposit_wizard=True)
        return super().create_invoices()
