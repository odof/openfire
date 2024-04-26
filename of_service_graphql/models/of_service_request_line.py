# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


class OFServiceRequestLine(models.Model):
    _inherit = 'of.service.request.line'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if qty := args.get('qty'):
            mutation['qty'] = qty

        if price_unit := args.get('price_unit'):
            mutation['price_unit'] = price_unit

        if price_subtotal := args.get('price_subtotal'):
            mutation['price_subtotal'] = price_subtotal

        if price_tax := args.get('price_tax'):
            mutation['price_tax'] = price_tax

        if price_total := args.get('price_total'):
            mutation['price_total'] = price_total

        if invoice_status := args.get('invoice_status'):
            mutation['invoice_status'] = invoice_status

        if qty_invoiced := args.get('qty_invoiced'):
            mutation['qty_invoiced'] = qty_invoiced

        if qty_invoicable := args.get('qty_invoicable'):
            mutation['qty_invoicable'] = qty_invoicable

        if product := args.get('product'):
            mutation['product'] = many2one(self=self, model='product.product', input=product)

        if order_line := args.get('order_line'):
            mutation['order_line'] = many2one(self=self, model='sale.order.line', input=order_line)

        if company := args.get('company'):
            mutation['company_id'] = many2one(self=self, model='res.company', input=company)

        if invoice_lines := args.get('invoice_lines'):
            mutation['invoice_line_ids'] = x2many(self=self, model='account.move', input=invoice_lines)

        return mutation
