# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare
import odoo.addons.decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_contains_kit = fields.Boolean(
        string="Contains a kit", compute='_compute_of_contains_kit', search='_search_of_contains_kit')
    comp_ids = fields.One2many(
        comodel_name='of.invoice.kit.line', inverse_name='invoice_id', string="Components",
        help="Contains all kit components in this invoice that are not kits themselves.")
    of_kit_display_mode = fields.Selection(
        [
            ('none', "None"),
            ('collapse', "Collapse"),
            ('expand', "Expand"),
        ], string="Kit display mode", default='expand',
        help="defines the way kits and their components should be printed out in pdf reports:\n"
             "- None: One line per kit. Nothing printed out about components\n"
             "- Collapse: One line per kit, with minimal info\n"
             "- Expand: One line per kit, plus one line per component")

    def _get_refund_prepare_fields(self):
        res = super(AccountInvoice, self)._get_refund_prepare_fields()
        return res + ['of_kit_display_mode']

    @api.multi
    @api.depends('invoice_line_ids.product_id')
    def _compute_of_contains_kit(self):
        comp_obj = self.env['of.invoice.kit.line']
        if self and isinstance(self[0].id, models.NewId):
            # Le calcul se situe dans un appel onchange
            # l'objet est donc unique, et il faut utiliser _origin au lieu de id
            self.of_contains_kit = comp_obj.search([('invoice_id', '=', self._origin.id)], count=True) > 0
        else:
            for invoice in self:
                invoice.of_contains_kit = comp_obj.search([('invoice_id', '=', invoice.id)], count=True) > 0

    @api.model
    def _search_of_contains_kit(self, operator, value):
        invoices = self.env['account.invoice.line'].search([('of_is_kit', '=', True)]).mapped('invoice_id')
        op = 'in' if (operator == '=') == value else 'not in'
        return [('id', op, invoices.ids)]

    @api.model
    def _refund_cleanup_lines(self, lines):
        # La création d'un avoir de facture implique la duplication de ses kits
        kit_obj = self.env['of.invoice.kit']
        result = super(AccountInvoice, self)._refund_cleanup_lines(lines)

        if lines._name == 'account.invoice.line':
            for vals in result:
                if vals[2].get('kit_id'):
                    vals[2]['kit_id'] = kit_obj.browse(vals[2]['kit_id']).copy().id
        return result

    def _prepare_invoice_line_from_po_line(self, line):
        data = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        data['of_pricing'] = 'fixed'
        return data


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    kit_id = fields.Many2one(comodel_name='of.invoice.kit', string="Components")
    of_is_kit = fields.Boolean(string="Is a kit")

    price_comps = fields.Float(
        string="Compo Price/Kit", compute='_compute_price_comps', oldname='unit_compo_price',
        help="Sum of the prices of all components necessary for 1 unit of this kit")
    cost_comps = fields.Monetary(
        string="Compo Cost/Kit", digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
        help="Sum of the costs of all components necessary for 1 unit of this kit")
    of_pricing = fields.Selection(
        [
            ('fixed', "Fixed"),
            ('computed', "Computed"),
        ], string="Pricing", required=True, default='fixed',
        help=u"""
            This field is only relevant if the product is a kit.
            It represents the way the price should be computed.\n
            If set to 'fixed', the price of it's components won't be taken into account
             and the price will be the one of the kit.\n
            If set to 'computed', the price will be computed according to the components of the kit.""")

    invoice_kits_to_unlink = fields.Boolean(
        string="account kits to unlink?", default=False,
        help="True if at least 1 account kit needs to be deleted from database")

    def get_kit_descr_collapse(self):
        """
        returns a string to be added to a kit name in PDF reports when kit display mode is set to 'Collapse'
        that string contains all components in this line that are not kits, plus their total quantities
        """
        self.ensure_one()
        if not self.of_is_kit:
            return ""
        components = self.kit_id.kit_line_ids
        ir_model_data = self.env['ir.model.data']
        units_id = ir_model_data.get_object_reference('product', 'product_uom_unit')[1]
        res = []
        for comp in components:
            qty_int_val = int(comp.qty_total)
            if comp.product_uom_id.id == units_id:  # uom is units, no need to print it
                qty = str(qty_int_val)  # qty is an int because it's in units
                comp_str = (comp.default_code or comp.name) + ": " + qty
            else:
                if qty_int_val == comp.qty_total:
                    qty = str(qty_int_val)
                else:
                    qty = str(comp.qty_total)
                comp_str = (comp.default_code or comp.name) + ": " + qty + " " + comp.product_uom_id.name
            res.append(comp_str)
        res = " (" + ", ".join(res) + ")"
        return res

    @api.onchange('quantity', 'uom_id')
    def _onchange_uom_id(self):
        self.ensure_one()
        super(AccountInvoiceLine, self)._onchange_uom_id()
        self._refresh_price_unit()

    @api.multi
    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        new_vals = {}
        if self.kit_id:  # former product was a kit -> unlink it's kit_id
            self.kit_id.write({'to_unlink': True})
            new_vals['kit_id'] = False
            new_vals['invoice_kits_to_unlink'] = True
        if not self.product_id:
            return res
        if self.product_id.of_is_kit:  # new product is a kit, we need to add its components
            new_vals['of_is_kit'] = True
            new_vals['of_pricing'] = self.product_id.of_pricing
            account_kit_vals = self.product_id.get_invoice_kit_data()
            account_kit_vals['qty_invoice_line'] = self.quantity
            new_vals['kit_id'] = self.env['of.invoice.kit'].create(account_kit_vals)
        else:  # new product is not a kit
            new_vals['of_is_kit'] = False
            new_vals['of_pricing'] = 'fixed'
        self.update(new_vals)
        return res

    @api.onchange('of_pricing')
    def _onchange_of_pricing(self):
        self.ensure_one()
        if self.of_pricing:
            if self.kit_id:
                self.kit_id.write({'of_pricing': self.of_pricing})
                self._refresh_price_unit()

    @api.onchange('kit_id')
    def _onchange_kit_id(self):
        self.ensure_one()
        if self.kit_id:
            self._compute_price_comps()
            self._refresh_price_unit()

    @api.depends('kit_id.kit_line_ids')
    def _compute_price_comps(self):
        for line in self:
            if line.of_is_kit:
                uc_price = 0
                uc_cost = 0
                if line.kit_id:
                    for comp in line.kit_id.kit_line_ids:
                        uc_price += comp.price_unit * comp.qty_per_kit
                        uc_cost += comp.cost_unit * comp.qty_per_kit
                line.price_comps = uc_price
                line.cost_comps = uc_cost

    @api.onchange('price_comps', 'quantity', 'of_pricing')
    def _refresh_price_unit(self):
        for line in self:
            if line.of_is_kit:
                price = line.price_unit
                option = line.sale_line_ids.mapped('of_order_line_option_id')
                if len(option) > 1:
                    option = False
                if line.of_pricing == 'computed':
                    # Option de ligne pour le prix de vente
                    if option and option.sale_price_update and line.price_comps:
                        if option.sale_price_update_type == 'fixed':
                            line.price_unit = line.price_comps + option.sale_price_update_value
                        elif option.sale_price_update_type == 'percent':
                            line.price_unit = line.price_comps + line.price_comps * (
                                    option.sale_price_update_value / 100)
                        line.price_unit = line.invoice_id.currency_id.round(line.price_unit)
                    else:
                        line.price_unit = line.price_comps
                    if line.price_unit != price:
                        line._compute_price()
                # Option de ligne pour le prix d'achat
                if option and option.purchase_price_update and line.cost_comps:
                    if option.purchase_price_update_type == 'fixed':
                        line.purchase_price = line.cost_comps + option.purchase_price_update_value
                    elif option.purchase_price_update_type == 'percent':
                        line.purchase_price = \
                            line.cost_comps * (1 + option.purchase_price_update_value / 100)
                    line.purchase_price = line.invoice_id.currency_id.round(line.purchase_price)
                else:
                    line.purchase_price = line.cost_comps

    @api.onchange('of_is_kit')
    def _onchange_of_is_kit(self):
        new_vals = {}
        if self.kit_id:  # former product was a kit -> unlink it's kit_id
            self.kit_id.write({'to_unlink': True})
            new_vals['kit_id'] = False
            new_vals['invoice_kits_to_unlink'] = True
        if self.of_is_kit:  # checkbox got checked
            if not self.product_id.of_is_kit:  # a product that is not a kit is being made into a kit
                # we create a component with current product (for procurements, kits are ignored)
                new_comp_vals = {
                    'product_id': self.product_id.id,
                    'name': self.product_id.name_get()[0][1] or self.product_id.name,
                    'qty_per_kit': 1,
                    'product_uom_id': self.uom_id.id or self.product_id.uom_id.id,
                    'price_unit': self.product_id.list_price,
                    'cost_unit': self.product_id.get_cost(),
                    'hide_prices': False,
                    }
                account_kit_vals = {
                    'of_pricing': 'computed',
                    'kit_line_ids': [(0, 0, new_comp_vals)],
                    }
                new_vals['kit_id'] = self.env['of.invoice.kit'].create(account_kit_vals)
                new_vals['of_pricing'] = 'computed'
            else:  # can happen if uncheck then recheck a kit
                new_vals['of_pricing'] = self.product_id.of_pricing
                account_kit_vals = self.product_id.get_invoice_kit_data()
                new_vals['kit_id'] = self.env['of.invoice.kit'].create(account_kit_vals)
        else:  # a product that was a kit is not anymore, we unlink its components
            new_vals['of_pricing'] = 'fixed'
            new_vals['price_unit'] = self.product_id.list_price
        self.update(new_vals)
        self._refresh_price_unit()

    def init_kit_from_so_line(self, so_line_id):
        # called by sale.order.line.invoice_line_create
        self.ensure_one()
        so_line = self.env['sale.order.line'].search([('id', '=', so_line_id)])
        if self.kit_id:
            self.kit_id.write({'to_unlink': True})
            self.write({'kit_id': False, 'invoice_kits_to_unlink': True})
        if so_line.kit_id:
            account_kit_vals = so_line.kit_id._prepare_account_kit(self.id)
            self.kit_id = self.env['of.invoice.kit'].create(account_kit_vals)
            self._refresh_price_unit()

    @api.model
    def create(self, vals):
        # from_so_line key added in vals in case of creation from a sale order
        from_so_line = vals.pop('from_so_line', False)
        if vals.get('invoice_kits_to_unlink'):
            self.sudo().env['of.invoice.kit'].search([('to_unlink', '=', True)]).unlink()
            vals.pop('invoice_kits_to_unlink')
        line = super(AccountInvoiceLine, self).create(vals)
        if line.of_is_kit and not from_so_line:
            account_kit_vals = {'invoice_line_id': line.id, 'name': line.name}
            line.kit_id.write(account_kit_vals)
            if line.of_pricing == 'computed':
                line.price_unit = line.price_comps
        return line

    @api.multi
    def write(self, vals):
        update_il_id = False
        if len(self._ids) == 1:
            if self.of_pricing == 'computed' and not float_compare(self.price_unit, self.price_comps, 2):
                vals['price_unit'] = self.price_comps
            if vals.get('invoice_kits_to_unlink') or self.invoice_kits_to_unlink:
                self.sudo().env['of.invoice.kit'].search([('to_unlink', '=', True)]).unlink()
                vals['invoice_kits_to_unlink'] = False
            if vals.get('kit_id') and not self.kit_id:
                # a account_invoice_kit was added
                update_il_id = True
            elif vals.get('name') and self.kit_id:
                # line changed name
                update_il_id = True
        super(AccountInvoiceLine, self).write(vals)
        if len(self) == 1 and (vals.get('of_pricing') or self.of_pricing) == 'computed':
            # Calcul réalisé après le premier write pour simplifier le calcul de l'option au cas où sale_line_ids
            # est modifié
            vals_price = {}
            # price_unit is equal to price_comps if pricing is computed
            price_comps = vals.get('kit_id') and self.env['of.invoice.kit'].browse(vals['kit_id']).price_comps or \
                          self.price_comps
            # Option de ligne pour le prix de vente
            option = self.sale_line_ids.mapped('of_order_line_option_id')
            if len(option) > 1:
                option = False
            if option and option.sale_price_update and price_comps:
                price_unit = 0.0
                if option.sale_price_update_type == 'fixed':
                    price_unit = price_comps + option.sale_price_update_value
                elif option.sale_price_update_type == 'percent':
                    price_unit = price_comps + price_comps * (option.sale_price_update_value / 100)
                vals_price['price_unit'] = self.invoice_id.currency_id.round(price_unit)
            else:
                vals_price['price_unit'] = price_comps
            super(AccountInvoiceLine, self).write(vals_price)
        if update_il_id:
            account_kit_vals = {'invoice_line_id': self.id}
            if vals.get('name'):
                account_kit_vals['name'] = vals.get('name')
            self.kit_id.write(account_kit_vals)
        return True

    @api.multi
    def copy_data(self, default=None):
        # La duplication d'une ligne de commande implique la duplication de son kit
        res = super(AccountInvoiceLine, self).copy_data(default)
        if res[0].get('kit_id'):
            res[0]['kit_id'] = self.kit_id.copy().id
        return res


class OfAccountInvoiceKit(models.Model):
    _name = 'of.invoice.kit'

    invoice_line_id = fields.Many2one(
        comodel_name='account.invoice.line', string="Invoice line", ondelete='cascade', copy=False)

    name = fields.Char(string="Name", required=True, default="draft invoice kit")
    kit_line_ids = fields.One2many(
        comodel_name='of.invoice.kit.line', inverse_name='kit_id', string="Components", copy=True)

    qty_invoice_line = fields.Float(string="Invoice Line Qty", related='invoice_line_id.quantity', readonly=True)
    currency_id = fields.Many2one(related='invoice_line_id.currency_id', store=True, string="Currency", readonly=True)
    price_comps = fields.Float(
        string="Compo Price/Kit", compute='_compute_price_comps',
        help="Sum of the prices of all components necessary for 1 unit of this kit", oldname='unit_compo_price')
    cost_comps = fields.Monetary(
        string="Compo Cost/Kit", digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
        help="Sum of the costs of all components necessary for 1 unit of this kit")

    to_unlink = fields.Boolean(string="to unlink?", default=False)
    of_pricing = fields.Selection(
        [
            ('fixed', "Fixed"),
            ('computed', "Computed"),
        ], string="Pricing", required=True, default='fixed',
        help="This field represents the way the price should be computed.\n"
             "if set to 'fixed', the price of it's components won't be taken into account"
             "and the price will be the one of the kit.\n"
             "if set to 'computed', the price will be computed according to the components of the kit.")

    @api.multi
    @api.depends('kit_line_ids')
    def _compute_price_comps(self):
        for kit in self:
            price = 0.0
            cost = 0.0
            if kit.kit_line_ids:
                for comp in kit.kit_line_ids:
                    price += comp.price_unit * comp.qty_per_kit
                    cost += comp.cost_unit * comp.qty_per_kit
                kit.price_comps = price
                kit.cost_comps = cost

    @api.model
    def _clear_db(self):
        not_linked = self.search([('invoice_line_id', '=', False)])
        kits_to_link = self.env['account.invoice.line'].search([('kit_id', 'in', not_linked._ids)])
        for kit in kits_to_link:
            kit.kit_id.invoice_line_id = kit.id
            not_linked -= kit.kit_id
        not_linked.unlink()


class OfAccountInvoiceKitLine(models.Model):
    _name = 'of.invoice.kit.line'
    _order = 'kit_id, sequence, id'

    kit_id = fields.Many2one(comodel_name='of.invoice.kit', string="Kit", ondelete='cascade')
    invoice_id = fields.Many2one(
        comodel_name='account.invoice', string="Invoice", related='kit_id.invoice_line_id.invoice_id')
    order_comp_id = fields.Many2one(comodel_name='of.saleorder.kit.line', string="Original comp")

    name = fields.Char(string="Name", required=True)
    default_code = fields.Char(related='product_id.default_code', string="Prod ref", readonly=True)
    sequence = fields.Integer(string="Sequence", default=10)

    product_id = fields.Many2one(
        comodel_name='product.product', string="Product", required=True, domain="[('of_is_kit', '=', False)]")
    currency_id = fields.Many2one(related='invoice_id.currency_id', string="Currency", readonly=True)
    product_uom_id = fields.Many2one(
        comodel_name='product.uom', string="UoM", readonly=True, related='product_id.uom_id')
    price_unit = fields.Monetary(
        string="Unit Price", digits=dp.get_precision('Product Price'), required=True, default=0.0, oldname='unit_price')
    price_unit_display = fields.Monetary(related='price_unit')
    cost_unit = fields.Monetary(string="Unit Cost", digits=dp.get_precision('Product Price'))
    cost_total = fields.Float(
        string="Subtotal Cost", compute='_compute_prices',
        help="Cost of this component total quantity. Equal to total quantity * unit cost.")
    cost_per_kit = fields.Monetary(
        string="Cost/Kit", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices',
        help="Cost of this component quantity necessary to make one unit of its invoice line kit."
             "Equal to quantity per kit unit * unit cost.")

    qty_per_kit = fields.Float(
        string="Qty / Kit", digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
        help="Quantity per kit unit (invoice line).\n"
             "example: 2 kit K1 -> 3 prod P. \n"
             "P.qty_per_kit = 3\n"
             "P.qty_total = 6")

    nb_kits = fields.Float(string="Number of kits", related='kit_id.qty_invoice_line', readonly=True)
    qty_total = fields.Float(
        string="Total Qty", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty_total',
        help="total quantity equal to quantity per kit times number of kits.")
    price_total = fields.Monetary(
        string="Subtotal Price", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices',
        help="Price of this component total quantity. Equal to total quantity * unit price.")
    price_per_kit = fields.Float(
        string="Price/Kit", compute='_compute_prices',
        help="Price of this component quantity necessary to make one unit of its invoice line kit."
             "Equal to quantity per kit unit * unit price.")
    kit_pricing = fields.Selection(related='kit_id.of_pricing', readonly=True)
    hide_prices = fields.Boolean(string="Hide prices", default=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # @TODO: handle case product is a kit (domain, error or load components
        if self.product_id:
            new_vals = {
                'name': self.product_id.name_get()[0][1] or self.product_id.name,
                'product_uom_id': self.product_id.product_tmpl_id.uom_id,
                'price_unit': self.product_id.list_price,
                'cost_unit': self.product_id.get_cost(),
            }
            if self.kit_id.invoice_line_id:
                if self.kit_id.invoice_line_id.of_pricing == 'fixed':
                    hide_prices = True
                else:
                    hide_prices = False
            else:
                hide_prices = self.hide_prices or False
            new_vals['hide_prices'] = hide_prices

            self.update(new_vals)

    @api.depends('price_unit', 'cost_unit', 'qty_per_kit', 'nb_kits')
    def _compute_prices(self):
        for comp in self:
            qty_per_kit = comp.qty_per_kit
            # prices
            comp.price_per_kit = comp.price_unit * qty_per_kit
            comp.price_total = comp.price_unit * qty_per_kit * comp.nb_kits
            # costs
            comp.cost_per_kit = comp.cost_unit * qty_per_kit
            comp.cost_total = comp.cost_unit * qty_per_kit * comp.nb_kits

    @api.depends('qty_per_kit', 'nb_kits')
    def _compute_qty_total(self):
        for comp in self:
            comp.qty_total = comp.qty_per_kit * comp.nb_kits

    @api.multi
    def get_report_name(self):
        self.ensure_one()
        # Inhibe l'affichage de la référence
        afficher_ref = self.env['ir.values'].get_default('account.config.settings', 'pdf_display_product_ref')
        if afficher_ref is None:
            # Test en théorie inutile
            # car ce module dépend de of_sale qui dépend de of_account_report qui définit pdf_display_product_ref
            afficher_ref = True

        self = self.with_context(
            lang=self.invoice_id.partner_id.lang,
            partner=self.invoice_id.partner_id.id,
        )
        name = self.name
        if not afficher_ref and name.startswith("["):
            pos = name.find(']')
            if pos != -1:
                name = name[pos+1:]
        return name.strip()
