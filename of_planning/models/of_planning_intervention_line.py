# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.float_utils import float_compare


class OFPlanningInterventionLine(models.Model):
    _name = 'of.planning.intervention.line'
    _description = "Intervention line"

    sequence = fields.Integer(default=10)
    name = fields.Text(string="Description")

    # Intervention Related fields
    intervention_id = fields.Many2one(
        comodel_name='calendar.event', string="Intervention", required=True, ondelete='cascade'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Partner", related='intervention_id.of_partner_id', readonly=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company', string="Company", related='intervention_id.of_company_id', readonly=True
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency', string="Currency", readonly=True, related='company_id.currency_id'
    )
    intervention_state = fields.Selection(
        related='intervention_id.of_state', string="Intervention state", copy=False, store=True, precompute=True
    )

    # Sale order related fields
    order_line_id = fields.Many2one(comodel_name='sale.order.line', string="Order line", copy=False)
    so_number = fields.Char(string="Sale order number", related='order_line_id.order_id.name', readonly=True)

    # Product & Quantity
    product_id = fields.Many2one(comodel_name='product.product', string="Product")
    qty = fields.Float(digits='Product Unit of Measure', default=1.0)
    qty_invoiceable = fields.Float(string="Invoiceable qty", compute='_compute_qty_invoiceable', store=True)
    qty_invoiced = fields.Float(string="Invoiced qty", compute='_compute_qty_invoiced', store=True)
    qty_delivered = fields.Float(string="Delivered qty", copy=False)
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_uom_id',
        store=True,
        readonly=False,
        precompute=True,
        ondelete='restrict',
    )

    # Picking
    move_ids = fields.One2many(comodel_name='stock.move', inverse_name='of_intervention_line_id', string="Stock Moves")

    # Pricing
    price_unit = fields.Float(
        string="Unit price",
        digits='Product Price',
        default=0.0,
        compute='_compute_price_unit',
        store=True,
        readonly=False,
    )
    discount = fields.Float(string="Discount (%)", digits='Discount', default=0.0)
    price_subtotal = fields.Monetary(
        compute='_compute_amount', string="Price subtotal", readonly=True, store=True, currency_field='currency_id'
    )
    price_tax = fields.Monetary(
        compute='_compute_amount', string="Taxes", readonly=True, store=True, currency_field='currency_id'
    )
    price_total = fields.Monetary(
        compute='_compute_amount', string="Price total", readonly=True, store=True, currency_field='currency_id'
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax', string="VAT", compute='_compute_tax_ids', store=True, readonly=False
    )

    # Invoicing
    invoice_line_ids = fields.One2many(
        comodel_name='account.move.line', inverse_name='of_intervention_line_id', string="Invoice line"
    )
    invoice_policy = fields.Selection(related='intervention_id.of_invoice_policy', string="Invoice policy")
    invoice_status = fields.Selection(
        selection=[
            ('no', "Nothing to Bill"),
            ('to invoice', "Waiting Bills"),
            ('invoiced', "Fully Billed"),
        ],
        string="Invoice status",
        compute='_compute_invoice_status',
        store=True,
    )

    # ------------------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------------------

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self.filtered(lambda li: li.product_id):
            line.price_unit = line.product_id.lst_price

    @api.depends('product_id')
    def _compute_uom_id(self):
        for line in self:
            if not line.uom_id or (line.product_id.uom_id.id != line.uom_id.id):
                line.uom_id = line.product_id.uom_id

    @api.depends('qty', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        """
        Compute the amount of the line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                price, line.currency_id, line.qty, product=line.product_id, partner=line.intervention_id.of_address_id
            )
            line.update(
                {
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                }
            )

    @api.depends(
        'invoice_policy',
        'intervention_state',
        'qty',
        'qty_delivered',
        'qty_invoiced',
        'order_line_id',
    )
    def _compute_qty_invoiceable(self):
        for line in self:
            if line.intervention_state not in ('confirmed', 'ongoing', 'done') or line.order_line_id:
                line.qty_invoiceable = 0.0
            elif line.invoice_policy == 'intervention':
                line.qty_invoiceable = line.qty - line.qty_invoiced
            elif line.invoice_policy == 'delivery':
                line.qty_invoiceable = line.qty_delivered - line.qty_invoiced

    @api.depends('intervention_state', 'qty', 'qty_delivered', 'qty_invoiced', 'order_line_id', 'qty_invoiceable')
    def _compute_invoice_status(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.intervention_state not in ['confirmed', 'ongoing', 'done'] or line.order_line_id:
                line.invoice_status = 'no'
            elif not float_is_zero(line.qty_invoiceable, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif float_compare(line.qty_invoiced, line.qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    @api.depends('invoice_line_ids', 'invoice_line_ids.move_id', 'invoice_line_ids.quantity')
    def _compute_qty_invoiced(self):
        for line in self:
            line.qty_invoiced = sum(line.mapped('invoice_line_ids.quantity'))

    @api.depends('product_id', 'company_id', 'partner_id')
    def _compute_tax_ids(self):
        for line in self:
            fiscal_position = line.intervention_id.of_fiscal_position_id
            taxes = line.company_id._of_filter_taxes(line.product_id.taxes_id)
            line.tax_ids = fiscal_position and fiscal_position.map_tax(taxes) or taxes

    # ------------------------------------------------------------------------------
    # Business methods
    # ------------------------------------------------------------------------------

    def _update_vals(self):
        for line in self.filtered(lambda line: line.order_line_id):
            order_line = line.order_line_id
            planned_qty = sum(
                order_line.of_intervention_line_ids.filtered(
                    lambda li: (li.intervention_id.of_state not in ('cancel', 'postponed') and li.id != line.id)
                ).mapped('qty')
            )
            qty = order_line.product_uom_qty - planned_qty
            line.update(
                {
                    'order_line_id': order_line.id,
                    'product_id': order_line.product_id.id,
                    'qty': qty,
                    'price_unit': order_line.price_unit,
                    'name': order_line.name,
                    'tax_ids': [Command.clear()] + [Command.link(tax.id) for tax in order_line.tax_id],
                }
            )

    def _get_delivered_qty(self):
        """Computes the delivered quantity on planning intervention lines, based on done stock moves related to
        its procurements.

        Returns:
            float: The delivered quantity.
        """
        self.ensure_one()
        qty = 0.0
        for move in self.move_ids.filtered(
            lambda m: m.state == 'done' and not m.scrapped and m.product_id == self.product_id
        ):
            if move.location_dest_id.usage == 'customer':
                if not move.origin_returned_move_id or move.to_refund:
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_id.uom_id)
            elif move.to_refund:
                qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_id.uom_id)
        return qty

    def _get_qty_procurement(self):
        """Calculate the quantity of procurement for the intervention line.

        This method calculates the quantity of procurement for the intervention line by summing up the quantities of
        outgoing moves and subtracting the quantities of incoming moves.

        Returns:
            float: The quantity of procurement for the intervention line.
        """
        self.ensure_one()
        qty = 0.0
        outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
        for move in outgoing_moves:
            qty += move.product_uom._compute_quantity(
                move.product_uom_qty, self.product_id.uom_id, rounding_method='HALF-UP'
            )
        for move in incoming_moves:
            qty -= move.product_uom._compute_quantity(
                move.product_uom_qty, self.product_id._uom_id, rounding_method='HALF-UP'
            )
        return qty

    def _get_outgoing_incoming_moves(self):
        """
        Get the outgoing and incoming stock moves related to the intervention line.

        Returns:
            tuple: A tuple containing two sets of stock moves - outgoing_moves and incoming_moves.
                The outgoing_moves set contains stock moves with the location destination usage as "customer"
                and either no origin_returned_move_id or to_refund flag is set.
                The incoming_moves set contains stock moves with the to_refund flag set.
        """
        outgoing_moves = self.env['stock.move']
        incoming_moves = self.env['stock.move']

        moves = self.move_ids.filtered(
            lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id
        )
        for move in moves:
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id or move.to_refund:
                    outgoing_moves |= move
            elif move.to_refund:
                incoming_moves |= move

        return outgoing_moves, incoming_moves

    def _get_procurement_group(self):
        return self.intervention_id.of_procurement_group_id

    def _prepare_procurement_group_vals(self):
        return {
            'name': self.intervention_id.name,
            'partner_id': self.intervention_id.of_address_id.id,
            'of_intervention_id': self.intervention_id.id,
        }

    def _prepare_procurement_values(self, group_id=False):
        """Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        self.ensure_one()
        date_deadline = self.intervention_id.start
        date_planned = date_deadline - timedelta(days=self.intervention_id.of_company_id.security_lead)
        return {
            'group_id': group_id,
            'of_intervention_line_id': self.id,
            'date_planned': date_planned,
            'date_deadline': date_deadline,
            'warehouse_id': self.intervention_id.of_warehouse_id or False,
            'partner_id': self.intervention_id.of_address_id.id,
            'product_description_variants': self.name,
            'company_id': self.intervention_id.of_company_id,
            'sequence': self.sequence,
        }

    def _action_launch_stock_rule(self):
        """
        Copied from sale.order.line._action_launch_stock_rule (`odoo/addons/sale_stock/models/sale_order_line.py`) and
        adapted to work with interventions.

        Launch procurement group run method with required/custom fields generated by a intervention line.
        Procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture' depending on the intervention line
        product rule.
        """
        if self._context.get('skip_procurement'):
            return True
        if not self.user_has_groups('of_planning.group_intervention_use_deliveries'):
            return True

        check_state = self._context.get('check_state', True)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        intervention_skipped = self.env['calendar.event']
        procurements = []
        line_treated = []
        for line in self:
            if not line.intervention_id.of_warehouse_id:
                raise UserError(
                    _("Please select a warehouse in the invoicing tab of the intervention: %s")
                    % line.intervention_id.name
                )

            line = line.with_company(line.company_id)
            if (
                (check_state and line.intervention_state not in ('confirmed', 'ongoing', 'done'))
                or line.product_id.type not in ('consu', 'product')
                or line.order_line_id
            ):
                continue
            if not line.intervention_id.of_address_id:
                intervention_skipped |= line.intervention_id

            qty = line._get_qty_procurement()
            if float_compare(qty, line.qty, precision_digits=precision) == 0:
                # La ligne a déjà été traitée dans une précédente génération de BL
                continue

            line_treated.append(line)
            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.intervention_id.of_procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.intervention_id.of_address_id:
                    updated_vals['partner_id'] = line.intervention_id.of_address_id.id
                if group_id.of_intervention_id != line.intervention_id:
                    updated_vals['of_intervention_id'] = line.intervention_id.id
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.qty - qty

            line_uom = line.uom_id
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(
                self.env['procurement.group'].Procurement(
                    line.product_id,
                    product_qty,
                    procurement_uom,
                    line.intervention_id.of_address_id.property_stock_customer,
                    line.product_id.display_name,
                    line.intervention_id.name,
                    line.intervention_id.of_company_id,
                    values,
                )
            )
        if procurements:
            procurement_group = self.env['procurement.group']
            if self.env.context.get('import_file'):
                procurement_group = procurement_group.with_context(import_file=False)
            procurement_group.run(procurements)

        if not line_treated:
            raise UserError(
                _("No product to add in a stock picking for the following intervention: %s")
                % self.mapped('intervention_id.name')
            )

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation
        # rather than stock.move confirmation
        interventions = self.mapped('intervention_id')
        for intervention in interventions:
            if pickings_to_confirm := intervention.of_picking_ids.filtered(lambda p: p.state not in ['cancel', 'done']):
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
        return True

    def _prepare_invoice_line(self):
        """
        Prepare the invoice line for the intervention.

        Returns:
            tuple: A tuple containing the invoice line data and an empty string or an error message.
        """
        self.ensure_one()
        line_data = {}
        messages = []

        product = self.product_id
        partner = self.partner_id
        fiscal_position = self.intervention_id.of_fiscal_position_id
        taxes = self.tax_ids
        if taxes:
            if company := self.intervention_id._get_invoicing_company(partner):
                taxes = taxes.filtered(lambda r: r.company_id == company)
        elif fiscal_position:
            taxes = fiscal_position.map_tax(taxes)

        line_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not line_account:
            messages.append(_("Income accounts must be configured for the product category \"%s\".") % product.name)
            return line_data, messages

        # Mapping des comptes par taxe induit par le module of_account_tax
        for tax in taxes:
            line_account = tax.map_account(line_account)

        line_name = self.name or product.name_get()[0][1]
        line_data |= {
            'name': line_name,
            'account_id': line_account.id,
            'price_unit': self.price_unit,
            'quantity': self.qty_invoiceable,
            'discount': 0.0,
            'product_uom_id': product.uom_id.id,
            'product_id': product.id,
            'tax_ids': [Command.set(taxes.ids)],
            'of_intervention_line_id': self.id,
        }
        return line_data, messages
