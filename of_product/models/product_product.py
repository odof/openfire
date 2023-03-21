# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    standard_price = fields.Float(of_unify_companies=True)
    of_theoretical_cost = fields.Float(
        string="Theoretical cost", digits='Product Price', groups="base.group_user",
        help="Corresponds to the cost calculated by applying the rules defined in the brand or in the import files."
             " This cost value can be used for margin calculation in quotes and invoices; however, it is never used "
             "for inventory valuation.")
    of_forced_lst_price = fields.Float(string="Sale price (forced)", digits='Product Price')

    @api.depends('list_price', 'price_extra', 'of_forced_lst_price')
    @api.depends_context('uom')
    def _compute_product_lst_price(self):
        if not self.env.user.has_group('of_product.group_product_variant_specific_price'):
            return super()._compute_product_lst_price()

        to_uom = None
        if 'uom' in self._context:
            to_uom = self.env['uom.uom'].browse(self._context['uom'])

        for product in self:
            list_price = product.of_forced_lst_price or product.list_price
            if to_uom:
                list_price = product.uom_id._compute_price(list_price, to_uom)
            product.lst_price = list_price

    @api.onchange('lst_price')
    def _set_product_lst_price(self):
        if not self.env.user.has_group('of_product.group_product_variant_specific_price'):
            return super()._set_product_lst_price()
        for product in self:
            if self._context.get('uom'):
                value = self.env['uom.uom'].browse(self._context['uom'])._compute_price(
                    product.lst_price, product.uom_id)
            else:
                value = product.lst_price
            product.write({'of_forced_lst_price': value})

    def price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        if self.env.user.has_group('of_product.group_product_variant_specific_price'):
            return super().price_compute('lst_price', uom=uom, currency=currency, company=company, date=date)
        return super().price_compute(price_type, uom=uom, currency=currency, company=company, date=date)

    @api.model
    def _add_missing_default_values(self, values):
        # Mettre la référence produit (default_code) du template par défaut lors de la création d'une variante.
        if 'product_tmpl_id' in values and values['product_tmpl_id']:
            values['default_code'] = self.env['product.template'].browse(values['product_tmpl_id']).default_code
        return super(ProductProduct, self)._add_missing_default_values(values)

    def _change_standard_price(self, new_price):
        """
        Override of the standard method in 'odoo/addons/stock_account/models/product.py' to update the standard price
        of all companies.

        Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        # Handle stock valuation layers.

        if self.filtered(
                lambda p: p.valuation == 'real_time') and not \
                self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(_(
                "You cannot update the cost of a product in automated valuation as it leads to the "
                "creation of a journal entry, for which you don't have the access rights."))

        companies = self.env['res.company'].search(  # OF
            ['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        for company in companies:  # OF
            svl_vals_list = []
            company_id = company.id  # OF
            for product in self:
                if product.cost_method not in ('standard', 'average'):
                    continue
                quantity_svl = product.sudo().quantity_svl
                if float_compare(quantity_svl, 0.0, precision_rounding=product.uom_id.rounding) <= 0:
                    continue
                digits = self.env['decimal.precision'].precision_get('Product Price')
                rounded_new_price = float_round(new_price, precision_digits=digits)
                diff = rounded_new_price - product.standard_price
                value = company_id.currency_id.round(quantity_svl * diff)
                if company_id.currency_id.is_zero(value):
                    continue

                svl_vals = {
                    'company_id': company_id.id,
                    'product_id': product.id,
                    'description': _('Product value manually modified (from %s to %s)') % (
                        product.standard_price, rounded_new_price),
                    'value': value,
                    'quantity': 0,
                }
                svl_vals_list.append(svl_vals)
            stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

            # Handle account moves.
            product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}
            am_vals_list = []
            for stock_valuation_layer in stock_valuation_layers:
                product = stock_valuation_layer.product_id
                value = stock_valuation_layer.value

                if product.type != 'product' or product.valuation != 'real_time':
                    continue

                # Sanity check.
                if not product_accounts[product.id].get('expense'):
                    raise UserError(
                        _("You must set a counterpart account on your product category."))
                if not product_accounts[product.id].get('stock_valuation'):
                    raise UserError(_(
                        "You don\'t have any stock valuation account defined on your product category."
                        "You must define one before processing this operation."))

                if value < 0:
                    debit_account_id = product_accounts[product.id]['expense'].id
                    credit_account_id = product_accounts[product.id]['stock_valuation'].id
                else:
                    debit_account_id = product_accounts[product.id]['stock_valuation'].id
                    credit_account_id = product_accounts[product.id]['expense'].id

                move_vals = {
                    'journal_id': product_accounts[product.id]['stock_journal'].id,
                    'company_id': company_id.id,
                    'ref': product.default_code,
                    'stock_valuation_layer_ids': [(6, None, [stock_valuation_layer.id])],
                    'move_type': 'entry',
                    'line_ids': [(0, 0, {
                        'name': _(
                            '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                            user=self.env.user.name,
                            previous=product.standard_price,
                            new_price=new_price,
                            product=product.display_name
                        ),
                        'account_id': debit_account_id,
                        'debit': abs(value),
                        'credit': 0,
                        'product_id': product.id,
                    }), (0, 0, {
                        'name': _(
                            '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                            user=self.env.user.name,
                            previous=product.standard_price,
                            new_price=new_price,
                            product=product.display_name
                        ),
                        'account_id': credit_account_id,
                        'debit': 0,
                        'credit': abs(value),
                        'product_id': product.id,
                    })],
                }
                am_vals_list.append(move_vals)

            account_moves = self.env['account.move'].sudo().create(am_vals_list)
            if account_moves:
                account_moves._post()

    def get_cost(self):
        if not self:
            return 0
        self.ensure_one()
        if self.cost_method == 'standard' or self.categ_id.of_sale_cost == 'standard':
            return self.standard_price
        else:
            return self.of_theoretical_cost

    @api.model_create_multi
    def create(self, vals_list):
        products = super(ProductProduct, self).create(vals_list)
        for product in products:
            if product.cost_method == 'standard':
                product.of_theoretical_cost = product.standard_price

            # FIXME: of_purchase_coeff_cost_propagation is from of_purchase module (not migrated yet)
            if 'of_purchase_coeff_cost_propagation' in dir(product):
                product.of_purchase_coeff_cost_propagation(product.get_cost())

        return products

    def write(self, values):
        res = super(ProductProduct, self).write(values)

        for product in self:
            if product.cost_method == 'standard':
                if 'standard_price' in values and values['standard_price'] != product.of_theoretical_cost:
                    product.of_theoretical_cost = product.standard_price
                elif 'of_theoretical_cost' in values and values['of_theoretical_cost'] != product.standard_price:
                    product.standard_price = product.of_theoretical_cost

            # FIXME: of_purchase_coeff_cost_propagation is from of_purchase module (not migrated yet)
            if 'of_purchase_coeff_cost_propagation' in dir(product):
                if (product.cost_method == 'standard' or product.categ_id.of_sale_cost == 'standard') and \
                        'standard_price' in values:
                    product.of_purchase_coeff_cost_propagation(product.standard_price)
                elif product.cost_method == 'standard' and product.categ_id.of_sale_cost == 'theoretical' and \
                        'of_theoretical_cost' in values:
                    product.of_purchase_coeff_cost_propagation(product.of_theoretical_cost)

        return res
