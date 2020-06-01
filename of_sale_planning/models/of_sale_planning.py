# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_compare, float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_invoice_policy = fields.Selection(
            selection_add=[('intervention', u'Quantités planifiées')])


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_qty_planifiee = fields.Float(string=u"Qtés planifiées", compute="_compute_of_qty_planifiee", store=True)

    @api.depends('of_intervention_line_ids', 'of_intervention_line_ids.qty', 'of_intervention_line_ids.intervention_state')
    def _compute_of_qty_planifiee(self):
        for line in self:
            lines = line.of_intervention_line_ids.filtered(lambda l: l.intervention_state in ('done', ))
            line.of_qty_planifiee = sum(lines.mapped('qty'))


    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy',
                 'of_qty_planifiee')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            invoice_policy = line.order_id.of_invoice_policy
            if not invoice_policy:
                invoice_policy = line.product_id.invoice_policy
            if line.order_id.state in ['sale', 'done']:
                if invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                elif invoice_policy == 'delivery':
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.of_qty_planifiee - line.qty_invoiced
            else:
                line.qty_to_invoice = 0


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    product_ids = fields.Many2many('product.product')


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    product_ids = fields.Many2many('product.product', related='template_id.product_ids')


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
