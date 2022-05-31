# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_duration = fields.Float(string=u"Durée de pose prévisionnelle", compute="_compute_of_duration")
    of_invoice_policy = fields.Selection(selection_add=[('intervention', u'Quantités planifiées')])

    @api.depends('order_line', 'order_line.of_duration')
    def _compute_of_duration(self):
        for order in self:
            order.of_duration = sum(order.order_line.mapped('of_duration'))

    @api.depends('of_invoice_policy', 'order_line', 'order_line.of_invoice_date_prev',
                 'order_line.procurement_ids', 'order_line.procurement_ids.move_ids',
                 'order_line.procurement_ids.move_ids.picking_id.min_date',
                 'order_line.of_intervention_line_ids', 'order_line.of_intervention_line_ids.intervention_id',
                 'order_line.of_intervention_line_ids.intervention_id.date')
    def _compute_of_invoice_date_prev(self):
        super(SaleOrder, self)._compute_of_invoice_date_prev()
        for order in self:
            if order.of_invoice_policy == 'intervention':
                interventions = order.order_line.mapped('of_intervention_line_ids').mapped('intervention_id')
                if interventions:
                    order.of_invoice_date_prev = interventions[0].date_date


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_duration = fields.Float(string=u"Durée de pose prévisionnelle")
    of_invoice_policy = fields.Selection(selection_add=[('intervention', u'Quantités planifiées')])

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy',
                 'of_qty_planifiee')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self.filtered(lambda l: l.of_invoice_policy == 'intervention'):
            if line.order_id.state in ['sale', 'done']:
                line.qty_to_invoice = line.of_qty_planifiee - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
        super(SaleOrderLine, self.filtered(lambda l: l.of_invoice_policy != 'intervention'))._get_to_invoice_qty()

    @api.depends('of_invoice_policy',
                 'order_id', 'order_id.of_fixed_invoice_date',
                 'of_intervention_line_ids', 'of_intervention_line_ids.intervention_id',
                 'of_intervention_line_ids.intervention_id.date')
    def _compute_of_invoice_date_prev(self):
        super(SaleOrderLine, self)._compute_of_invoice_date_prev()
        for line in self:
            if line.of_invoice_policy == 'intervention':
                interventions = line.of_intervention_line_ids.mapped('intervention_id')
                if interventions:
                    line.of_invoice_date_prev = interventions[0].date_date

    @api.multi
    def calculate_duration(self):
        if self.of_is_kit and self.kit_id:
            kit_lines = self.kit_id.kit_line_ids
            total_duration = 0.0
            for kit_line in kit_lines:
                original_uom = kit_line.product_id.uom_id
                current_uom = kit_line.product_uom_id
                qty = kit_line.qty_per_kit
                product_duration = kit_line.product_id.of_duration_per_unit
                total_duration += (product_duration * current_uom._compute_quantity(qty, original_uom, round=False))
            self.of_duration = total_duration * self.product_uom_qty
        elif self.product_id:
            original_uom = self.product_id.uom_id
            current_uom = self.product_uom
            self.of_duration = self.product_id.of_duration_per_unit * \
                current_uom._compute_quantity(self.product_uom_qty, original_uom, round=False)

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        self.calculate_duration()
        return res

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        super(SaleOrderLine, self).product_uom_change()
        self.calculate_duration()

    @api.onchange('of_is_kit')
    def _onchange_of_is_kit(self):
        super(SaleOrderLine, self)._onchange_of_is_kit()
        self.calculate_duration()

    @api.onchange('kit_id')
    def _onchange_kit_id(self):
        super(SaleOrderLine, self)._onchange_kit_id()
        self.calculate_duration()

    @api.model
    def _new_line_for_template(self, data):
        new_line = super(SaleOrderLine, self)._new_line_for_template(data)
        new_line.calculate_duration()
        return new_line


class OFSaleOrderLayoutCategory(models.Model):
    _inherit = 'of.sale.order.layout.category'

    of_duration = fields.Float(string=u"Heures", compute='_compute_of_duration')

    @api.multi
    def _compute_of_duration(self):
        for line in self:
            line.of_duration = sum(line.order_line_ids.mapped('of_duration'))


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_invoice_policy = fields.Selection(selection_add=[('intervention', u'Facturer les quantités planifiées')])
