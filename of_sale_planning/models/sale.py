# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_duration = fields.Float(string=u"Durée de pose prévisionnelle", compute="_compute_of_duration")
    of_invoice_policy = fields.Selection(selection_add=[('intervention', u'Quantités planifiées')])

    @api.depends('order_line', 'order_line.of_duration_total')
    def _compute_of_duration(self):
        for order in self:
            order.of_duration = sum(order.order_line.mapped('of_duration_total'))

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

    @api.model
    def _auto_init(self):
        res = super(SaleOrderLine, self)._auto_init()
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_sale_planning')])
        if module_self:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_self.latest_version
            if version < '10.0.2':
                cr = self.env.cr
                cr.execute("UPDATE sale_order_line SET of_duration_per_unit = (of_duration / product_uom_qty) "
                           "WHERE of_duration != 0 AND product_uom_qty != 0;")
        return res

    of_duration = fields.Float(string=u"Durée de pose prévisionnelle") # A supprimer à l'avenir
    of_duration_per_unit = fields.Float(string=u"Durée de pose prévisionnelle unitaire")
    of_duration_total = fields.Float(
        string=u"Durée de pose prévisionnelle totale", compute='_compute_of_duration_total', store=True)
    of_invoice_policy = fields.Selection(selection_add=[('intervention', u'Quantités planifiées')])

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy',
                 'of_qty_planning_done')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self.filtered(lambda l: l.of_invoice_policy == 'intervention'):
            if line.order_id.state in ['sale', 'done']:
                line.qty_to_invoice = line.of_qty_planning_done - line.qty_invoiced
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

    @api.depends('of_is_kit', 'product_id', 'of_duration_per_unit', 'product_uom_qty')
    def _compute_of_duration_total(self):
        for line in self:
            if line.of_is_kit:
                line.of_duration_total = line.of_duration_per_unit * line.product_uom_qty
            elif line.product_id:
                original_uom = line.product_id.uom_id
                current_uom = line.product_uom
                try:
                    line.of_duration_total = line.of_duration_per_unit * current_uom._compute_quantity(
                        line.product_uom_qty, original_uom, round=False)
                except UserError:
                    line.of_duration_total = line.of_duration_per_unit * line.product_uom_qty

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
            self.of_duration_per_unit = total_duration
        elif self.product_id:
            self.of_duration_per_unit = self.product_id.of_duration_per_unit

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        self.calculate_duration()
        return res

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
            line.of_duration = sum(line.order_line_ids.mapped('of_duration_total'))


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_invoice_policy = fields.Selection(selection_add=[('intervention', u'Facturer les quantités planifiées')])
