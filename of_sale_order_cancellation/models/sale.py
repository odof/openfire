# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_commercially_cancelled = fields.Boolean(string=u"Commande annulée commerciallement", copy=False)
    of_cancellation_order = fields.Boolean(string=u"Commande d'annulation", copy=False)

    @api.depends('state', 'order_line.invoice_status', 'of_force_invoice_status', 'of_cancellation_order')
    def _get_invoiced(self):
        super(SaleOrder, self)._get_invoiced()
        for order in self:
            if order.of_cancellation_order:
                order.invoice_status = 'no'

    @api.multi
    def button_commercial_cancellation(self):
        self.ensure_one()

        if self.state != 'sale':
            raise UserError(u"Seules les commandes validées peuvent être annulées commercialement !")

        # Création d'une commande inverse
        cancel_order = self.copy(default={'of_cancellation_order': True,
                                          'origin': self.name,
                                          'client_order_ref': self.client_order_ref,
                                          'opportunity_id': self.opportunity_id.id,
                                          'project_id': self.project_id.id,
                                          'campaign_id': self.campaign_id.id,
                                          'medium_id': self.medium_id.id,
                                          'source_id': self.source_id.id,
                                          'of_referred_id': self.of_referred_id.id})
        cancel_order.order_line.mapped(lambda line: line.write({'product_uom_qty': -line.product_uom_qty}))
        cancel_order.with_context(order_cancellation=True).action_confirm()

        # Annulation des objets liés à la commande d'origine

        # Annulation BLs
        self.picking_ids.filtered(lambda p: not any(move.state == 'done' for move in p.move_lines)).action_cancel()

        # Annulation factures brouillons
        self.invoice_ids.filtered(lambda i: i.state == 'draft').action_invoice_cancel()

        # Annulation demandes de prix
        self.env['purchase.order'].search([('sale_order_id', '=', self.id), ('state', '=', 'draft')]).button_cancel()

        # Annulation suivi
        if self.of_followup_project_id:
            self.of_followup_project_id.set_to_canceled()

        self.of_commercially_cancelled = True
        # On bloque la commande annulée
        self.action_done()

        action = self.env.ref('sale.action_orders').read()[0]
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['res_id'] = cancel_order.id

        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy',
                 'order_id.of_cancellation_order')
    def _compute_invoice_status(self):
        super(SaleOrderLine, self)._compute_invoice_status()
        for line in self:
            if line.order_id.of_cancellation_order:
                line.invoice_status = 'no'
