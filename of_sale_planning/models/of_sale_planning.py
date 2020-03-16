# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_compare, float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_invoice_policy = fields.Selection(
            selection_add=[('intervention', u'Quantités planifiées')])

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

    of_invoice_policy = fields.Selection(
        selection_add=[('intervention', u'Quantités planifiées')])

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy',
                 'of_qty_planifiee')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            invoice_policy = line.of_invoice_policy
            if line.order_id.state in ['sale', 'done']:
                if invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                elif invoice_policy == 'delivery':
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.of_qty_planifiee - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

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


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_invoice_policy = fields.Selection(
            selection_add=[('intervention', u'Facturer les quantités planifiées')])


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_invoice_policy = fields.Selection(
        selection_add=[('intervention', u'Quantités planifiées')])


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    invoice_policy = fields.Selection(
        selection_add=[('intervention', u'Quantités planifiées')])
