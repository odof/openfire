# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, SUPERUSER_ID
import odoo.addons.decimal_precision as dp
from odoo.tools.misc import formatLang
from odoo.tools.float_utils import float_round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


@api.multi
def unlink(self):
    """
    On surcharge la fonction unlink() de cette façon par besoin d'insérer notre test sur les mouvements de stock
    entre le test sur l'état annulé et le super().
    """
    stock_move_obj = self.env['stock.move']
    for order in self:
        if not order.state == 'cancel':
            raise UserError(_('In order to delete a purchase order, you must cancel it first.'))
        if self.env.uid != SUPERUSER_ID:
            move_lines = stock_move_obj.search([('origin', '=', order.name), ('state', '!=', 'cancel')])
            # L'admin garde la possibilité de supprimer une CF
            if move_lines:
                raise UserError(u"Vous ne pouvez supprimer une commande fournisseur, "
                                u"même annulée, qui a des mouvements de stock non annulés.")
    return super(Purchase, self).unlink()


Purchase.unlink = unlink


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    customer_id = fields.Many2one('res.partner', string='Client')
    customer_shipping_id = fields.Many2one(comodel_name='res.partner', string=u"Adresse de Livraison du Client")
    customer_shipping_city = fields.Char(
        related='customer_shipping_id.city', string=u"Ville", store=True, readonly=True, compute_sudo=True)
    customer_shipping_zip = fields.Char(
        related='customer_shipping_id.zip', string=u"Code Postal", store=True, readonly=True, compute_sudo=True)
    sale_order_id = fields.Many2one('sale.order', string=u"Commande d'origine")
    delivery_expected = fields.Char(string='Livraison attendue', states={'done': [('readonly', True)]})
    of_sent = fields.Boolean(string=u"CF envoyée", copy=False)
    of_project_id = fields.Many2one(comodel_name='account.analytic.account', string=u"Compte analytique")
    of_user_id = fields.Many2one(comodel_name='res.users', string="Responsable technique")
    of_reception_state = fields.Selection(selection=[
        ('no', u'Non reçue'),
        ('received', u'Reçue')], string=u"État de réception", compute='_compute_of_reception_state',
        compute_sudo=True, store=True)
    of_delivery_force = fields.Datetime(string=u"Forcer date prévue")

    @api.depends('order_line.move_ids', 'order_line.move_ids.picking_id.state')
    def _compute_of_reception_state(self):
        for order in self:
            if order.picking_ids and all([state == 'done' for state in order.picking_ids.filtered(
                    lambda p: p.state not in ['cancel']).mapped('state')]):
                order.of_reception_state = 'received'
            else:
                order.of_reception_state = 'no'

    @api.model
    def create(self, vals):
        if self.env['ir.values'].get_default('purchase.config.settings', 'of_date_purchase_order'):
            vals['date_order'] = fields.Datetime.now()
        return super(PurchaseOrder, self).create(vals)

    @api.model
    def _prepare_picking(self):
        values = super(PurchaseOrder, self)._prepare_picking()
        values['of_customer_id'] = self.customer_id.id
        if self.partner_id:
            addresses = self.partner_id.address_get(['delivery'])
            values['partner_shipping_id'] = addresses['delivery']
        if self.customer_id:
            addresses = self.customer_id.address_get(['delivery'])
            values['of_customer_shipping_id'] = addresses['delivery']
        return values

    @api.multi
    def button_confirm(self):
        super(PurchaseOrder, self).button_confirm()
        if self.env['ir.values'].get_default('sale.config.settings', 'of_recalcul_pa'):
            self._update_purchase_price()

    @api.multi
    def button_draft(self):
        """
        Surcharge basée sur ce que fait button_cancel mais on tente de faire l'inverse
        """
        res = super(PurchaseOrder, self).button_draft()
        for order in self:
            # on va chercher les procurement.order à l'état annulé uniquement
            procurements = order.order_line.mapped('procurement_ids').filtered(lambda r: r.state == 'cancel')
            moves = procurements.filtered(lambda r: r.rule_id.propagate).mapped('move_dest_id')
            moves_filtered = moves.filtered(lambda r: r.state == 'cancel')
            procurements |= moves_filtered.mapped('procurement_id').filtered(lambda r: r.state == 'cancel')
            # on a trouvé tous les procurement.order, on les repasse à l'état confirmé si possible
            procurements.reset_to_confirmed()
            # ceux qui ont réussi vont remettre l'état du stock.move à waiting
            procurements.filtered(lambda r: r.state == 'confirmed').mapped('move_dest_id').write({'state': 'waiting'})
            # le check final pour confirmer que tout est correct
            procurements.check()
        return res

    @api.multi
    def button_update_purchase_price(self):
        self._update_purchase_price()

    @api.multi
    def _update_purchase_price(self):
        procurement_obj = self.env['procurement.order']
        for order in self:
            for line in order.order_line:
                procurements = procurement_obj.search([('purchase_line_id', '=', line.id)])
                moves = procurements.mapped('move_dest_id')
                sale_lines = moves.mapped('procurement_id').mapped('sale_line_id')
                sale_lines.write({'of_seller_price': line.price_unit,
                                  'purchase_price': line.price_unit * line.product_id.property_of_purchase_coeff})

    @api.multi
    def action_view_invoice(self):
        result = super(PurchaseOrder, self).action_view_invoice()
        if not self.invoice_ids:
            result['context']['default_company_id'] = self.company_id.id
        else:
            result['context']['default_company_id'] = self.invoice_ids[0].company_id.id
        return result

    @api.multi
    def action_set_date_planned(self):
        for order in self:
            order.order_line.update({'date_planned': order.of_delivery_force})

    @api.multi
    @api.depends('name', 'partner_ref')
    def name_get(self):
        if self._context.get('purchase_amount_total', False):
            # keep the standard if purchase_amount_total is set in the context
            return super(PurchaseOrder, self).name_get()
        result = []
        for po in self:
            name = po.name
            if po.partner_ref:
                name += ' (' + po.partner_ref + ')'
            if po.amount_untaxed:
                name += ': ' + formatLang(self.env, po.amount_untaxed, currency_obj=po.currency_id)
            result.append((po.id, name))
        return result

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        self.ensure_one()
        addresses = self.customer_id.address_get(['delivery'])
        self.customer_shipping_id = addresses['delivery']


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_total_stock_qty = fields.Float(
        string=u"Stock total", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_of_stock_qty')
    of_available_stock_qty = fields.Float(
        string=u"Stock dispo.", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_of_stock_qty')
    of_theoretical_stock_qty = fields.Float(
        string=u"Stock théo.", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_of_stock_qty',
        help=u"Si une règle de stock est définie pour l'article avec une date limite de prévision, le stock théorique "
             u"est calculé à cette date ; sinon le stock théorique calculé est le stock théorique global de l'article")
    of_reserved_qty = fields.Float(
        string=u"Qté(s) réservée(s)", digits=dp.get_precision('Product Unit of Measure'),
        compute='_compute_of_stock_qty')

    @api.depends('product_id', 'order_id.picking_type_id', 'order_id.picking_type_id.default_location_dest_id')
    def _compute_of_stock_qty(self):
        for line in self:
            if line.order_id.picking_type_id.default_location_dest_id:
                location = line.order_id.picking_type_id.default_location_dest_id
                product_context = dict(self._context, location=location.id)

                # Stock total
                line.of_total_stock_qty = line.product_id.with_context(product_context).qty_available

                # Stock dispo
                domain_quant = [('product_id', '=', line.product_id.id), ('reservation_id', '=', False)]
                domain_quant += line.product_id.with_context(product_context)._get_domain_locations()[0]
                quants = self.env['stock.quant'].search(domain_quant)
                line.of_available_stock_qty = float_round(
                    sum(quants.mapped('qty')), precision_rounding=line.product_id.uom_id.rounding)

                # Stock théorique
                orderpoints = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', line.product_id.id)],
                                                                            limit=1)
                if orderpoints and orderpoints.of_forecast_limit:
                    product_context['of_to_date_expected'] = \
                        (datetime.today() + relativedelta(
                            days=orderpoints.of_forecast_period
                        )).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                line.of_theoretical_stock_qty = line.product_id.with_context(product_context).virtual_available

                # Qté(s) réservée(s)
                stock_moves = line.procurement_ids.mapped('move_ids')
                if stock_moves:
                    domain_quant = [('product_id', '=', line.product_id.id), ('reservation_id', 'in', stock_moves.ids)]
                    domain_quant += line.product_id.with_context(product_context)._get_domain_locations()[0]
                    quants = self.env['stock.quant'].search(domain_quant)
                    line.of_reserved_qty = float_round(
                        sum(quants.mapped('qty')), precision_rounding=line.product_id.uom_id.rounding)
                else:
                    line.of_reserved_qty = 0

            else:
                line.of_total_stock_qty = 0
                line.of_available_stock_qty = 0
                line.of_theoretical_stock_qty = 0
                line.of_reserved_qty = 0

    @api.multi
    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        if 'price_unit' in vals:
            # On répercute le changement de prix pour la valorisation de l'inventaire s'il y a lieu
            moves = self.mapped('move_ids')
            if moves:
                moves.write({'price_unit': vals['price_unit']})
                quants = moves.mapped('quant_ids')
                if quants:
                    quants.sudo().write({'cost': vals['price_unit']})
        return res
