# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import math

from odoo import api, fields, models
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Composants de kits
    # Un champ classique pour faciliter l'édition
    comp_ids = fields.One2many(
        'of.saleorder.kit.line', 'order_id', string='Components',
        help="Contains all kit components in this sale order."
    )
    of_contains_kit = fields.Boolean(
        string='Contains a kit', compute='_compute_of_contains_kit', search='_search_of_contains_kit'
    )
    of_kit_display_mode = fields.Selection(
        [
            ('none', 'None'),
            ('collapse', 'Collapse'),
            ('expand', 'Expand'),
        ], string='Kit display mode', default='expand',
        help="defines the way kits and their components should be printed out in pdf reports:\n"
             "- None: One line per kit. Nothing printed out about components\n"
             "- Collapse: One line per kit, with minimal info\n"
             "- Expand: One line per kit, plus one line per component"
    )
    of_difference = fields.Boolean(compute='_compute_of_difference', readonly=True)

    @api.depends('order_line', 'order_line.of_difference')
    def _compute_of_difference(self):
        for order in self:
            if order.order_line.filtered('of_difference'):
                order.of_difference = True
            else:
                order.of_difference = False

    @api.multi
    @api.depends('order_line.product_id')
    def _compute_of_contains_kit(self):
        comp_obj = self.env['of.saleorder.kit.line']
        if self and isinstance(self[0].id, models.NewId):
            # Le calcul se situe dans un appel onchange
            # l'objet est donc unique, et il faut utiliser _origin au lieu de id
            self.of_contains_kit = comp_obj.search([("order_id", "=", self._origin.id)], count=True) > 0
        else:
            for order in self:
                order.of_contains_kit = comp_obj.search([("order_id", "=", order.id)], count=True) > 0

    @api.model
    def _search_of_contains_kit(self, operator, value):
        orders = self.env['sale.order.line'].search([('of_is_kit', '=', True)]).mapped('order_id')
        op = 'in' if (operator == '=') == value else 'not in'
        return [('id', op, orders.ids)]

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order.
        Override of parent function
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_kit_display_mode'] = self.of_kit_display_mode
        return invoice_vals

    @api.multi
    def action_draft(self):
        # Retrait du lien des approvisionnements avec les composants de kits.
        # Cela permettra d'en générer de nouveaux à la confirmation de la commande.
        # Code copié depuis le module sale.
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        super(SaleOrder, self).action_draft()
        return orders.mapped('comp_ids').mapped('procurement_ids').write({'of_sale_comp_id': False})

    @api.multi
    def action_cancel(self):
        # Annulation des approvisionnements liés aux composants de kits.
        # Code copié depuis le module sale_stock
        self.mapped('comp_ids').mapped('procurement_ids').cancel()
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def of_action_wizard_insert_kit_comps(self):
        wizard = self.env['of.wizard.insert.kit.comps'].create({})
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'of.wizard.insert.kit.comps',
            'res_id': wizard.id,
            'target': 'new',
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    kit_id = fields.Many2one('of.saleorder.kit', string="Components", copy=True)
    of_is_kit = fields.Boolean(string='Is a kit')

    price_comps = fields.Float(
        string='Compo Price/Kit', compute='_compute_price_comps',
        help="Sum of the prices of all components necessary for 1 unit of this kit", oldname="unit_compo_price"
    )
    cost_comps = fields.Monetary(
        string='Compo Cost/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
        help="Sum of the costs of all components necessary for 1 unit of this kit"
    )
    of_pricing = fields.Selection(
        [
            ('fixed', 'Fixed'),
            ('computed', 'Computed'),
        ], string="Pricing", required=True, default='fixed',
        help="This field is only relevant if the product is a kit. It represents the way the price should be computed.\n"
             "if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit.\n"
             "if set to 'computed', the price will be computed according to the components of the kit."
    )
    of_difference = fields.Boolean(compute='_compute_of_difference', store=True)

    sale_kits_to_unlink = fields.Boolean(
        string="sale kits to unlink?", default=False,
        help="True if at least 1 sale kit needs to be deleted from database"
    )

    def _compute_margin(self, order_id, product_id, product_uom_id):
        if not product_id.of_is_kit:
            return super(SaleOrderLine, self)._compute_margin(order_id, product_id, product_uom_id)
        frm_cur = self.env.user.company_id.currency_id
        to_cur = order_id.pricelist_id.currency_id
        purchase_price = product_id.cost_comps
        if product_uom_id != product_id.uom_id:
            purchase_price = product_id.uom_id._compute_price(purchase_price, product_uom_id)
        ctx = self.env.context.copy()
        ctx['date'] = order_id.date_order
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return price

    @api.depends('kit_id.kit_line_ids', 'kit_id', 'kit_id.kit_line_ids.cost_unit',
                 'kit_id.kit_line_ids.price_unit', 'kit_id.kit_line_ids.qty_per_kit')
    def _compute_price_comps(self):
        for line in self:
            if line.kit_id:
                line.price_comps = line.kit_id.price_comps
                line.cost_comps = line.kit_id.cost_comps

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

    @api.onchange('price_comps', 'cost_comps', 'of_pricing', 'product_id')
    def _refresh_price_unit(self):
        for line in self:
            if line.order_id.state == 'done':
                # Impossible de modifier les montants d'une commande verrouillée
                continue
            if line.of_is_kit:
                if line.of_pricing == 'computed':
                    price = line.price_unit
                    line.price_unit = line.price_comps
                    if line.price_unit != price:
                        line._compute_amount()
                line.purchase_price = line.cost_comps

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        new_vals = {}
        if self.kit_id:  # former product was a kit -> unlink it's kit_id
            self.kit_id.write({"to_unlink": True})
            new_vals['kit_id'] = False
            new_vals["sale_kits_to_unlink"] = True
        if not self.product_id:
            return res
        if self.product_id.of_is_kit:  # new product is a kit, we need to add its components
            new_vals['of_is_kit'] = True
            new_vals['of_pricing'] = self.product_id.of_pricing
            sale_kit_vals = self.product_id.get_saleorder_kit_data()
            sale_kit_vals["qty_order_line"] = self.product_uom_qty
            new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)
        else:  # new product is not a kit
            new_vals['of_is_kit'] = False
            new_vals['of_pricing'] = 'fixed'
        self.update(new_vals)
        return res

    @api.onchange('product_uom_qty', 'product_uom')
    def product_uom_change(self):
        self.ensure_one()
        super(SaleOrderLine, self).product_uom_change()
        self._refresh_price_unit()

    @api.depends('qty_invoiced', 'product_uom_qty', 'order_id.state', 'order_id.of_invoice_policy',
                 'order_id.partner_id.of_invoice_policy', 'procurement_ids', 'procurement_ids.move_ids',
                 'procurement_ids.move_ids.of_ordered_qty', 'procurement_ids.move_ids.picking_id',
                 'procurement_ids.move_ids.picking_id.state')
    def _get_to_invoice_qty(self):
        for line in self.filtered(lambda l: l.of_invoice_policy == 'ordered_delivery' and l.of_is_kit):
            if line.order_id.state in ['sale', 'done']:
                line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
        super(SaleOrderLine, self.filtered(lambda l: l.of_invoice_policy != 'ordered_delivery' or not l.of_is_kit)).\
            _get_to_invoice_qty()

    @api.depends('of_invoice_policy',
                 'order_id', 'order_id.of_fixed_invoice_date',
                 'procurement_ids', 'procurement_ids.move_ids', 'procurement_ids.move_ids.picking_id',
                 'procurement_ids.move_ids.picking_id.min_date', 'procurement_ids.move_ids.picking_id.state',
                 'kit_id', 'kit_id.kit_line_ids', 'kit_id.kit_line_ids.procurement_ids',
                 'kit_id.kit_line_ids.procurement_ids.move_ids',
                 'kit_id.kit_line_ids.procurement_ids.move_ids.picking_id',
                 'kit_id.kit_line_ids.procurement_ids.move_ids.picking_id.min_date',
                 'kit_id.kit_line_ids.procurement_ids.move_ids.picking_id.state')
    def _compute_of_invoice_date_prev(self):
        super(SaleOrderLine, self)._compute_of_invoice_date_prev()
        for line in self:
            if line.of_invoice_policy == 'ordered_delivery' and line.of_is_kit:
                moves = line.kit_id.kit_line_ids.mapped('procurement_ids').mapped('move_ids')
                moves = moves.filtered(lambda m: m.picking_id.state != 'cancel').sorted('date_expected')

                if moves:
                    to_process_moves = moves.filtered(lambda m: m.picking_id.state != 'done')
                    if to_process_moves:
                        line.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(to_process_moves[0].date_expected))
                    else:
                        line.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(moves[-1].date_expected))

    @api.onchange('of_pricing')
    def _onchange_of_pricing(self):
        self.ensure_one()
        if self.of_pricing:
            if self.kit_id:
                self.kit_id.write({'of_pricing': self.of_pricing})
                self._refresh_price_unit()

    @api.onchange('of_is_kit')
    def _onchange_of_is_kit(self):
        new_vals = {}
        if self.kit_id:  # former product was a kit -> unlink it's kit_id
            self.kit_id.write({"to_unlink": True})
            new_vals["kit_id"] = False
            new_vals["sale_kits_to_unlink"] = True
        if self.of_is_kit:  # checkbox got checked
            if not self.product_id.of_is_kit:  # a product that is not a kit is being made into a kit
                # we create a component with current product (for procurements, kits are ignored)
                new_comp_vals = {
                    'product_id': self.product_id.id,
                    'name': self.product_id.name_get()[0][1] or self.product_id.name,
                    'qty_per_kit': 1,
                    'product_uom_id': self.product_uom.id or self.product_id.uom_id.id,
                    'price_unit': self.product_id.list_price,
                    'cost_unit': self.product_id.standard_price,
                    'customer_lead': self.product_id.sale_delay,
                    'hide_prices': False,
                    }
                sale_kit_vals = {
                    'of_pricing': 'computed',
                    'kit_line_ids': [(0, 0, new_comp_vals)],
                    }
                new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)
                new_vals["of_pricing"] = "computed"
            else:  # can happen if uncheck then recheck a kit
                new_vals['of_pricing'] = self.product_id.of_pricing
                sale_kit_vals = self.product_id.get_saleorder_kit_data()
                new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)

        else:  # a product that was a kit is not anymore, we unlink its components
            new_vals["of_pricing"] = 'fixed'
            new_vals["price_unit"] = self.product_id.list_price
        self.update(new_vals)
        self._refresh_price_unit()

    @api.onchange('kit_id')
    def _onchange_kit_id(self):
        self.ensure_one()
        if self.kit_id:
            self._compute_price_comps()
            self._refresh_price_unit()

    @api.multi
    def _action_procurement_create(self):
        """
        Creates a procurement order for lines in self. Call ._action_procurement_create() on components.
        """
        lines = self.filtered(lambda line: not line.of_is_kit)  # get all lines in self that are not kits
        res_order_lines = super(SaleOrderLine, lines)._action_procurement_create()  # create POs for those lines

        kits = self - lines  # get all lines that are kits
        # get all comps
        components = self.env['of.saleorder.kit.line'].search([('kit_id.order_line_id', 'in', kits._ids)])
        res_order_comps = components._action_procurement_create()
        return res_order_lines + res_order_comps

    @api.multi
    def _get_delivered_qty_hack(self):
        """
        Computes the delivered quantity on sale order lines, based on done stock moves related to its procurements.
        At the moment we use an all or nothing policy for kits delivery.
        hack because of mrp_bom vs sale order lines that are kit made from BoMs
        """
        self.ensure_one()
        if not self.of_is_kit:
            qty = super(SaleOrderLine, self)._get_delivered_qty()
            return qty
        delivered_qty = 0.0
        for component in self.kit_id.kit_line_ids.filtered(lambda l: l.qty_per_kit):
            delivered_qty = max(math.ceil(round(component.qty_delivered / component.qty_per_kit, 3)), delivered_qty)
        return delivered_qty

    @api.multi
    def _all_comps_delivered(self):
        """
        Check if all components were delivered entirely.
        (This method is no longer used but we keep it in case we need it again.)
        """
        self.ensure_one()
        components = self.kit_id.kit_line_ids or []
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        inclure_service = self.env['ir.values'].get_default('sale.config.settings', 'of_inclure_service_bl')
        for comp in components:
            if not inclure_service and comp.product_id.type == "service":
                continue
            if comp.qty_delivered < comp.qty_total \
                    and not float_is_zero(comp.qty_delivered - comp.qty_total, precision_digits=precision):
                return False
        return True

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.
        override to add 'of_is_kit' and 'of_pricing' fields. Components will be loaded after creation of the line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.of_is_kit:
            res['of_is_kit'] = True
            res['of_pricing'] = self.of_pricing
        else:
            res['of_pricing'] = 'fixed'
            res['of_is_kit'] = False
        return res

    @api.multi
    def invoice_line_create(self, invoice_id, qty):
        """
        Create an invoice line. The quantity to invoice can be positive (invoice) or negative
        (refund).
        split sale order lines between regular lines and kit lines

        :param invoice_id: integer
        :param qty: float quantity to invoice
        """
        kit_lines = self.env['sale.order.line']
        other_lines = self.env['sale.order.line']
        for line in self:
            if line.of_is_kit:
                kit_lines |= line
            else:
                other_lines |= line

        super(SaleOrderLine, other_lines).invoice_line_create(invoice_id, qty)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        ai_line_obj = self.env['account.invoice.line']
        for line in kit_lines:
            if not float_is_zero(qty, precision_digits=precision):
                vals = line._prepare_invoice_line(qty=qty)
                vals.update({
                    'invoice_id': invoice_id,
                    'sale_line_ids': [(6, 0, [line.id])],
                    'from_so_line': True,
                    })
                new_line = ai_line_obj.create(vals)
                # now new_line has an id
                new_line.init_kit_from_so_line(line.id)

    @api.model
    def create(self, vals):
        if vals.get("sale_kits_to_unlink"):
            self.sudo().env["of.saleorder.kit"].search([("to_unlink", "=", True)]).unlink()
            vals.pop("sale_kits_to_unlink")
        line = super(SaleOrderLine, self).create(vals)
        sale_kit_vals = {'order_line_id': line.id, 'name': line.name, 'of_pricing': line.of_pricing}
        line.kit_id.write(sale_kit_vals)
        # Doit être rappeler pour les kits sinon les liens pour la création d'approvisionnements n'existent pas
        if line.kit_id and line.order_id.state == 'sale':
            line._action_procurement_create()
        return line

    @api.multi
    def write(self, vals):
        if vals.get("sale_kits_to_unlink") or self.filtered(lambda l: l.sale_kits_to_unlink):
            self.sudo().env["of.saleorder.kit"].search([("to_unlink", "=", True)]).unlink()
            vals["sale_kits_to_unlink"] = False
        update_ol_id = False
        if len(self) == 1 and vals.get("kit_id") and not self.kit_id:
            # a sale_order_kit was added
            update_ol_id = True
        elif len(self) == 1 and vals.get("name") and self.kit_id:
            # line changed name
            update_ol_id = True
        elif 'of_pricing' in vals:
            update_ol_id = True
        if len(self) == 1 and vals.get('of_pricing', self.of_pricing) == 'computed' \
                and vals.get('of_is_kit', self.of_is_kit):
            vals['price_unit'] = vals.get('kit_id') and self.env['of.saleorder.kit'].browse(vals['kit_id']).price_comps\
                                 or self.price_comps  # price_unit is equal to price_comps if pricing is computed
        super(SaleOrderLine, self).write(vals)
        if update_ol_id:
            sale_kit_vals = {'order_line_id': self.id}
            if vals.get("name"):
                sale_kit_vals["name"] = vals.get("name")
            if vals.get("of_pricing"):
                sale_kit_vals["of_pricing"] = vals.get("of_pricing")
            self.kit_id.write(sale_kit_vals)
        if len(self) == 1 and 'kit_id' in vals:
            if not vals.get('kit_id'):
                self.env['of.saleorder.kit'].search([('order_line_id', '=', self.id)]).unlink()
            else:
                self.env['of.saleorder.kit'].search(
                    [('order_line_id', '=', self.id), ('id', '!=', vals.get('kit_id'))]).unlink()
        return True

    @api.multi
    def _write(self, vals):
        if len(vals.keys()) == 1 and vals.get('of_difference'):
            # Permet de forcer un recalcul du prix unitaire, la valeur ainsi forcée ne sera prise en compte que si
            # l'utilisateur ne sauvegarde pas la ligne, le devis ou les deux
            self._refresh_price_unit()
            vals['of_difference'] = False
        res = super(SaleOrderLine, self)._write(vals)
        return res

    @api.multi
    def copy_data(self, default=None):
        # La duplication d'une ligne de commande implique la duplication de son kit
        res = super(SaleOrderLine, self).copy_data(default)
        if res[0].get('kit_id'):
            res[0]['kit_id'] = self.kit_id.copy().id
        return res

    @api.depends('of_pricing', 'price_unit',
                 'kit_id', 'kit_id.kit_line_ids',
                 'kit_id.kit_line_ids.price_unit',
                 'kit_id.kit_line_ids.qty_per_kit')
    def _compute_of_difference(self):
        for line in self:
            kit_pricing = self._context.get('current_of_pricing', line.of_pricing)
            if line.kit_id and kit_pricing == 'computed':
                line.of_difference = float_compare(line.kit_id.price_comps, line.price_unit, 2)
            else:
                line.of_difference = False

    @api.multi
    def refresh_cost_comps(self):
        for line in self:
            if line.kit_id:
                line.purchase_price = line.cost_comps


class OfSaleOrderKit(models.Model):
    _name = 'of.saleorder.kit'

    order_line_id = fields.Many2one("sale.order.line", string="Order line", ondelete="cascade", copy=False)

    name = fields.Char(string='Name', required=True, default="draft saleorder kit")
    kit_line_ids = fields.One2many('of.saleorder.kit.line', 'kit_id', string="Components", copy=True)

    qty_order_line = fields.Float(string="Order Line Qty", related="order_line_id.product_uom_qty", readonly=True)
    currency_id = fields.Many2one(related='order_line_id.currency_id', store=True, string='Currency', readonly=True)
    price_comps = fields.Float(
        string='Compo Price/Kit', compute='_compute_price_comps',
        help="Sum of the prices of all components necessary for 1 unit of this kit", oldname="unit_compo_price")
    cost_comps = fields.Float(
        string='Compo Cost/Kit', compute='_compute_price_comps',
        help="Sum of the costs of all components necessary for 1 unit of this kit")
    qty_invoiced = fields.Float(related="order_line_id.qty_invoiced", readonly=True)
    state = fields.Selection(
        [
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('sale', 'Sale Order'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ], related='order_line_id.state', string='Order Status', copy=False, default='draft'
    )
    to_unlink = fields.Boolean(string="to unlink?", default=False)
    of_pricing = fields.Selection([
        ('fixed', 'Fixed'),
        ('computed', 'Computed')
        ], string="Pricing", required=True, default='computed',
        help="This field represents the way the price should be computed.\n"
             "if set to 'fixed', the price of it's components won't be taken into account"
             "and the price will be the one of the kit.\n"
             "if set to 'computed', the price will be computed according to the components of the kit."
    )

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

    @api.multi
    def _prepare_account_kit(self, inv_line_id):
        """
        Prepare the dict of values to create a new invoice line comp

        :param inv_line_id: id of the invoice line where to put these comps
        """
        self.ensure_one()
        account_kit_vals = {
            'name': self.name,
            'of_pricing': self.of_pricing,
            'invoice_line_id': inv_line_id,
            'to_unlink': self.to_unlink,
            }
        lines = [(5,)]
        comp_vals = {}
        for line in self.kit_line_ids:
            comp_vals = line._prepare_account_kit_comp()
            lines.append((0, 0, comp_vals))
        account_kit_vals["kit_line_ids"] = lines
        return account_kit_vals

    @api.multi
    def account_kit_create(self, inv_line_id):
        account_kit_obj = self.env['of.invoice.kit']
        for kit in self:
            account_kit_vals = kit._prepare_account_kit(inv_line_id)
            account_kit_obj.create(account_kit_vals)

    @api.model
    def _clear_db(self):
        not_linked = self.search([('order_line_id', '=', False)])
        kits_to_link = self.env['sale.order.line'].search([('kit_id', 'in', not_linked._ids)])
        for kit in kits_to_link:
            kit.kit_id.order_line_id = kit.id
            not_linked -= kit.kit_id
        not_linked.unlink()


class OfSaleOrderKitLine(models.Model):
    _name = 'of.saleorder.kit.line'
    _order = "kit_id, sequence, id"

    kit_id = fields.Many2one('of.saleorder.kit', string="Kit", ondelete="cascade")
    order_id = fields.Many2one('sale.order', string="Order", related="kit_id.order_line_id.order_id")

    name = fields.Char(string='Name', required=True)
    default_code = fields.Char(related='product_id.default_code', string='Prod ref', readonly=True)
    sequence = fields.Integer(string=u'Sequence', default=10)

    product_id = fields.Many2one(
        'product.product', string='Product', required=True, domain="[('of_is_kit', '=', False)]"
    )
    currency_id = fields.Many2one(related='order_id.currency_id', string='Currency', readonly=True)
    product_uom_id = fields.Many2one('product.uom', string='UoM', readonly=True, related='product_id.uom_id')
    price_unit = fields.Monetary(
        string='Unit Price', digits=dp.get_precision('Product Price'), required=True, default=0.0, oldname="unit_price"
    )
    price_unit_display = fields.Monetary(related='price_unit')
    cost_unit = fields.Monetary('Unit Cost', digits=dp.get_precision('Product Price'))
    cost_total = fields.Monetary(
        string='Subtotal Cost', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices',
        help="Cost of this component total quantity. Equal to total quantity * unit cost."
    )
    cost_per_kit = fields.Monetary(
        string='Cost/Kit', compute='_compute_prices',
        help="Cost of this component quantity necessary to make one unit of its order line kit."
             "Equal to quantity per kit unit * unit cost."
    )

    qty_per_kit = fields.Float(
        string='Qty / Kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
        oldname="qty_per_line",
        help="Quantity per kit unit (order line).\n"
             "example: 2 kit K1 -> 3 prod P.\n"
             "P.qty_per_kit = 3\n"
             "P.qty_total = 6"
    )

    nb_kits = fields.Float(string='Number of kits', related='kit_id.qty_order_line', readonly=True)
    qty_total = fields.Float(
        string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty_total',
        help='total quantity equal to quantity per kit times number of kits.')
    price_total = fields.Monetary(
        string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices',
        help="Price of this component total quantity. Equal to total quantity * unit price.",
        oldname="price_per_line_total"
    )
    price_per_kit = fields.Monetary(
        string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices',
        help="Price of this component quantity necessary to make one unit of its order line kit."
             "Equal to quantity per kit unit * unit price."
    )
    kit_pricing = fields.Selection(related="kit_id.of_pricing", readonly=True)
    hide_prices = fields.Boolean(string="Hide prices", default=False)
    state = fields.Selection(
        [
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('sale', 'Sale Order'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ], related='order_id.state', string='Order Status', readonly=True, copy=False, store=True, default='draft'
    )

    customer_lead = fields.Float(
        string='Delivery Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer")
    procurement_ids = fields.One2many('procurement.order', 'of_sale_comp_id', string='Procurements')

    qty_delivered = fields.Float(
        string='Delivered Qty', copy=False, digits=dp.get_precision('Product Unit of Measure'), default=0.0
    )
    qty_delivered_updateable = fields.Boolean(
        compute='_compute_qty_delivered_updateable', string='Can Edit Delivered', readonly=True, default=True
    )
    invoiced = fields.Boolean("Invoiced", compute="_compute_invoiced")  # for readonly in XML
    route_id = fields.Many2one('stock.location.route', string="Route", compute="_compute_route")

    @api.depends('kit_id', 'kit_id.order_line_id', 'kit_id.order_line_id.route_id')
    def _compute_route(self):
        """ Reprend la route de la ligne de commande """
        for kit_line in self:
            kit_line.route_id = kit_line.kit_id.order_line_id.route_id.id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # @TODO: handle case product is a kit (domain, error or load components
        if self.product_id:
            new_vals = {
                'name': self.product_id.name_get()[0][1] or self.product_id.name,
                'product_uom_id': self.product_id.product_tmpl_id.uom_id,
                'price_unit': self.product_id.list_price,
                'cost_unit': self.product_id.standard_price,
                'customer_lead': self.product_id.sale_delay,
            }
            new_vals['hide_prices'] = self.kit_id.order_line_id and self.kit_id.order_line_id.of_pricing == 'fixed'
            self.update(new_vals)

    @api.multi
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

    @api.multi
    @api.depends('qty_per_kit', 'nb_kits')
    def _compute_qty_total(self):
        for comp in self:
            comp.qty_total = comp.qty_per_kit * comp.nb_kits

    @api.multi
    @api.depends("kit_id")
    def _compute_invoiced(self):
        for kit_line in self:
            kit_line.invoiced = kit_line.kit_id.order_line_id and kit_line.kit_id.order_line_id.qty_invoiced

    @api.multi
    @api.depends('product_id.invoice_policy', 'order_id.state')
    def _compute_qty_delivered_updateable(self):
        for line in self:
            line.qty_delivered_updateable = (line.order_id.state == 'sale') \
                                            and (line.product_id.track_service == 'manual') \
                                            and (line.product_id.expense_policy == 'no')

    @api.multi
    def _prepare_order_comp_procurement(self, group_id=False):
        self.ensure_one()
        return {
            'name': self.name,
            'origin': self.order_id.name,
            'date_planned': datetime.strptime(self.order_id.date_order, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(
                days=self.customer_lead),
            'product_id': self.product_id.id,
            'product_qty': self.qty_total,
            'product_uom': self.product_uom_id.id,
            'company_id': self.order_id.company_id.id,
            'group_id': group_id,
            'location_id': self.order_id.partner_shipping_id.property_stock_customer.id,
            'route_ids': self.kit_id.order_line_id.route_id and [(4, self.route_id.id)] or [],
            'warehouse_id': self.order_id.warehouse_id and self.order_id.warehouse_id.id or False,
            'partner_dest_id': self.order_id.partner_shipping_id.id,
            'of_sale_comp_id': self.id,
        }

    @api.multi
    def _action_procurement_create(self):
        """
        Copy of sale.order.line._action_procurement_create()
        Create procurements based on quantity ordered. If the quantity is increased, new
        procurements are created. If the quantity is decreased, no automated action is taken.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        new_procs = self.env['procurement.order']  # Empty recordset
        for comp in self:
            # Dans certains cas le champ comp.state n'est pas bien recalculé donc vérification via comp.order_id.state
            if (comp.state or comp.order_id.state) != 'sale' or not comp.product_id._need_procurement():
                continue
            qty = 0.0
            for proc in comp.procurement_ids:
                qty += proc.product_qty
            if float_compare(qty, comp.qty_total, precision_digits=precision) >= 0:
                continue

            if not comp.order_id.procurement_group_id:
                vals = comp.order_id._prepare_procurement_group()
                comp.order_id.procurement_group_id = self.env["procurement.group"].create(vals)

            vals = comp._prepare_order_comp_procurement(group_id=comp.order_id.procurement_group_id.id)
            vals['product_qty'] = comp.qty_total - qty
            new_proc = self.env["procurement.order"].with_context(procurement_autorun_defer=True).create(vals)
            new_proc.message_post_with_view('mail.message_origin_link',
                                            values={'self': new_proc, 'origin': comp.order_id},
                                            subtype_id=self.env.ref('mail.mt_note').id)
            new_procs += new_proc
        new_procs.run()
        orders = list(set(x.order_id for x in self))
        for order in orders:
            reassign = order.picking_ids.filtered(
                lambda x: x.state == 'confirmed' or ((x.state in ['partially_available', 'waiting']) and not x.printed))
            if reassign:
                reassign.do_unreserve()
                reassign.action_assign()
        return new_procs

    @api.multi
    def _get_delivered_qty(self):
        """
        Computes the delivered quantity on sale order line components,
        based on done stock moves related to its procurements.
        """
        self.ensure_one()
        qty = 0.0
        for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id:
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom_id)
            elif move.location_dest_id.usage == "internal" and move.to_refund_so:
                qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom_id)
        return qty

    @api.multi
    def _prepare_account_kit_comp(self):
        """
        Prepare the dict of values to create a new account.kit.line

        :param kit_id: id of the invoice line where to put these comps
        """
        self.ensure_one()
        new_comp_vals = {
            'name': self.name,
            'sequence': self.sequence,
            'price_unit': self.price_unit,
            'product_uom_id': self.product_uom_id.id,
            'product_id': self.product_id.id or False,
            'order_comp_id': self.id,
            'cost_unit': self.cost_unit,
            'qty_per_kit': self.qty_per_kit,
            'hide_prices': self.hide_prices,
        }
        return new_comp_vals

    @api.multi
    def get_report_name(self):
        self.ensure_one()
        # inhiber l'affichage de la référence
        afficher_ref = self.env['ir.values'].get_default('sale.config.settings', 'pdf_display_product_ref_setting')
        self = self.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
        )
        name = self.name
        if not afficher_ref and name.startswith("["):
            pos = name.find(']')
            if pos != -1:
                name = name[pos+1:]
        return name.strip()

    @api.multi
    def write(self, values):
        lines = False
        if 'qty_per_kit' in values:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            lines = self.filtered(
                lambda r: r.order_id.state == 'sale' and float_compare(r.qty_per_kit, values['qty_per_kit'],
                                                                       precision_digits=precision) == -1)
        res = super(OfSaleOrderKitLine, self).write(values)
        if lines:
            lines._action_procurement_create()
        return res

    @api.model
    def create(self, values):
        res = super(OfSaleOrderKitLine, self).create(values)
        if res.order_id.state == 'sale':
            res._action_procurement_create()
        return res
