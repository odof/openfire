# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_round


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _default_warehouse_id(self):
        return self.env.user.company_id.of_default_warehouse_id

    warehouse_id = fields.Many2one(default=lambda self: self._default_warehouse_id())
    of_picking_min_date = fields.Datetime(
        compute=lambda x: False, search='_search_of_picking_min_date', string="Date bon de livraison")
    of_picking_date_done = fields.Datetime(
        compute=lambda x: False, search='_search_of_picking_date_done', string="Date transfert bon de livraison")
    of_route_id = fields.Many2one('stock.location.route', string="Route")

    of_invoice_policy = fields.Selection(
        selection_add=[('ordered_delivery', u'Quantités commandées à date de livraison')])

    @api.onchange('of_route_id')
    def onchange_route(self):
        """ Permet de modifier la route utilisée des lignes de commande depuis le devis """
        if self.of_route_id:
            for line in self.order_line:
                line.route_id = self.of_route_id.id

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.warehouse_id = self.company_id.of_default_warehouse_id

    @api.model
    def _search_of_picking_min_date(self, operator, value):
        pickings = self.env['stock.picking'].search([('min_date', operator, value)])
        order_ids = []
        if pickings:
            self._cr.execute(
                "SELECT o.id "
                "FROM sale_order AS o "
                "INNER JOIN stock_picking AS p ON p.group_id = o.procurement_group_id "
                "WHERE p.id IN %s", (tuple(pickings._ids), ))
            order_ids = [row[0] for row in self._cr.fetchall()]
        return [('id', 'in', order_ids)]

    @api.model
    def _search_of_picking_date_done(self, operator, value):
        pickings = self.env['stock.picking'].search([('date_done', operator, value)])
        order_ids = []
        if pickings:
            self._cr.execute(
                "SELECT o.id "
                "FROM sale_order AS o "
                "INNER JOIN stock_picking AS p ON p.group_id = o.procurement_group_id "
                "WHERE p.id IN %s", (tuple(pickings._ids), ))
            order_ids = [row[0] for row in self._cr.fetchall()]
        return [('id', 'in', order_ids)]

    @api.depends('of_invoice_policy', 'order_line', 'order_line.of_invoice_date_prev',
                 'order_line.procurement_ids', 'order_line.procurement_ids.move_ids',
                 'order_line.procurement_ids.move_ids.picking_id',
                 'order_line.procurement_ids.move_ids.picking_id.min_date',
                 'order_line.procurement_ids.move_ids.picking_id.state')
    def _compute_of_invoice_date_prev(self):
        super(SaleOrder, self)._compute_of_invoice_date_prev()
        for order in self:
            if order.of_invoice_policy == 'ordered_delivery':
                pickings = order.order_line.mapped('procurement_ids') \
                    .mapped('move_ids') \
                    .mapped('picking_id') \
                    .filtered(lambda p: p.state != 'cancel') \
                    .sorted('min_date')
                if pickings:
                    to_process_pickings = pickings.filtered(lambda p: p.state != 'done')
                    if to_process_pickings:
                        order.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(to_process_pickings[0].min_date))
                    else:
                        order.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(pickings[-1].min_date))


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_invoice_policy = fields.Selection(
        selection_add=[('ordered_delivery', u'Quantités commandées à date de livraison')])
    of_stock_moves_state = fields.Selection(
        selection=[('draft', u"Nouveau"),
                   ('cancel', u"Annulé"),
                   ('waiting', u"En attente de réception"),
                   ('confirmed', u"Attente de disponibilité"),
                   ('assigned', u"Disponible"),
                   ('done', u"Fait")], string=u"État de suivi", compute='_compute_of_stock_moves_state', store=True)
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
    of_picking_min_week = fields.Char(
        string=u"Sem. de livraison prévue", compute='_compute_of_picking_min_week', store=True)
    of_receipt_min_week = fields.Char(string=u"Sem. de réception prévue", compute='_compute_of_receipt_min_week')
    of_product_type = fields.Selection(
        selection=[('product', u"Produit stockable"),
                   ('consu', u"Consommable"),
                   ('service', u"Service")], string=u"Type d'article", related='product_id.type', readonly=True,
        store=True)
    of_supplier_delivery_delay = fields.Float(
        string=u"Délai de livraison", compute='_compute_of_supplier_delivery_delay', store=True, compute_sudo=True)
    of_has_reordering_rule = fields.Boolean(
        string=u"Gérer sur règle de stock", compute='_compute_of_has_reordering_rule',
        help=u"L'article dispose de règles de réapprovisionnement.")
    of_client_order_ref = fields.Char(string=u"Référence Client", related='order_id.client_order_ref', readonly=True)

    @api.onchange('route_id')
    def _get_route_id(self):
        """ Permet de mettre la valeur par défaut de 'Route'
        (ne peut pas utiliser le contexte en xml car écrasé par une autre vue,
        ne pas transformer en champ calculé pour éviter la perte de données,
        ne peut pas mettre de fonction pour la valeur par défaut car appelé avant
        celle de 'order_id' ce qui empêche de peupler)
        """
        for line in self:
            if line.order_id and line.order_id.of_route_id and not line.route_id:
                line.route_id = line.order_id.of_route_id.id

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        # Inhiber la vérification de stock
        afficher_warning = self.env['ir.values'].get_default('sale.config.settings', 'of_stock_warning_setting')
        if afficher_warning:
            return super(SaleOrderLine, self)._onchange_product_id_check_availability()

    @api.depends('qty_invoiced', 'product_uom_qty', 'order_id.state', 'order_id.of_invoice_policy',
                 'order_id.partner_id.of_invoice_policy', 'procurement_ids', 'procurement_ids.move_ids',
                 'procurement_ids.move_ids.of_ordered_qty', 'procurement_ids.move_ids.picking_id',
                 'procurement_ids.move_ids.picking_id.state')
    def _get_to_invoice_qty(self):
        for line in self.filtered(lambda l: l.of_invoice_policy == 'ordered_delivery'):
            if line.order_id.state in ['sale', 'done']:
                moves = line.procurement_ids.mapped('move_ids')
                # On filtre les mouvements :
                #     - On ne prend pas les 'extra moves'
                #     - Le BL doit être validé ou il doit s'agir d'un reliquat annulé
                moves = moves.filtered(
                    lambda m: m.origin and
                              (m.picking_id.state == 'done' or (m.picking_id.state == 'cancel' and m.picking_id.backorder_id))
                    )
                line.qty_to_invoice = sum(moves.mapped('of_ordered_qty')) - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
        super(SaleOrderLine, self.filtered(lambda l: l.of_invoice_policy != 'ordered_delivery'))._get_to_invoice_qty()

    @api.depends('of_invoice_policy',
                 'order_id', 'order_id.of_fixed_invoice_date',
                 'procurement_ids', 'procurement_ids.move_ids', 'procurement_ids.move_ids.picking_id',
                 'procurement_ids.move_ids.picking_id.min_date', 'procurement_ids.move_ids.picking_id.state')
    def _compute_of_invoice_date_prev(self):
        super(SaleOrderLine, self)._compute_of_invoice_date_prev()
        for line in self:
            if line.of_invoice_policy == 'ordered_delivery':
                moves = line.procurement_ids.mapped('move_ids')
                moves = moves.filtered(lambda m: m.picking_id.state != 'cancel').sorted('date_expected')

                if moves:
                    to_process_moves = moves.filtered(lambda m: m.picking_id.state != 'done')
                    if to_process_moves:
                        line.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(to_process_moves[0].date_expected))
                    else:
                        line.of_invoice_date_prev = fields.Date.to_string(
                            fields.Date.from_string(moves[-1].date_expected))

    @api.depends('procurement_ids', 'procurement_ids.move_ids', 'procurement_ids.move_ids.state')
    def _compute_of_stock_moves_state(self):
        for line in self:
            stock_moves = line.procurement_ids.mapped('move_ids')
            if stock_moves:
                if stock_moves.filtered(lambda m: m.state == 'draft'):
                    line.of_stock_moves_state = 'draft'
                elif stock_moves.filtered(lambda m: m.state == 'waiting'):
                    line.of_stock_moves_state = 'waiting'
                elif stock_moves.filtered(lambda m: m.state == 'confirmed'):
                    line.of_stock_moves_state = 'confirmed'
                elif stock_moves.filtered(lambda m: m.state == 'assigned'):
                    line.of_stock_moves_state = 'assigned'
                elif stock_moves.filtered(lambda m: m.state == 'cancel'):
                    line.of_stock_moves_state = 'cancel'
                elif stock_moves.filtered(lambda m: m.state == 'done'):
                    line.of_stock_moves_state = 'done'
                else:
                    line.of_stock_moves_state = False
            else:
                line.of_stock_moves_state = False

    @api.depends('product_id', 'order_id.warehouse_id', 'order_id.warehouse_id.lot_stock_id')
    def _compute_of_stock_qty(self):
        for line in self:
            if line.order_id.warehouse_id:
                location = line.order_id.warehouse_id.lot_stock_id
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
                        (datetime.today() + relativedelta(days=orderpoints.of_forecast_period)). \
                            strftime(DEFAULT_SERVER_DATETIME_FORMAT)
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

    @api.depends('procurement_ids', 'procurement_ids.move_ids', 'procurement_ids.move_ids.picking_id',
                 'procurement_ids.move_ids.picking_id.move_lines',
                 'procurement_ids.move_ids.picking_id.move_lines.date_expected')
    def _compute_of_picking_min_week(self):
        for line in self:
            pickings = line.procurement_ids.mapped('move_ids').mapped('picking_id')
            if pickings:
                line.of_picking_min_week = pickings[0].of_min_week
            else:
                line.of_picking_min_week = ""

    @api.depends('procurement_ids', 'procurement_ids.move_ids')
    def _compute_of_receipt_min_week(self):
        for line in self:
            moves = line.procurement_ids.mapped('move_ids')
            if moves:
                purchase_procurement_orders = self.env['procurement.order'].search(
                    [('move_dest_id', 'in', moves.ids)])
                purchase_procurement_orders = purchase_procurement_orders.filtered(
                    lambda p: p.purchase_line_id.order_id.state == 'purchase')
                purchase_moves = purchase_procurement_orders.mapped('move_ids')
                min_date = min(purchase_moves.mapped('date_expected') or [False])
                if min_date:
                    min_year = fields.Date.from_string(min_date).year
                    min_week = datetime.strptime(min_date, "%Y-%m-%d %H:%M:%S").date().isocalendar()[1]
                    line.of_receipt_min_week = "%s - S%02d" % (min_year, min_week)
                else:
                    line.of_receipt_min_week = ""
            else:
                line.of_receipt_min_week = ""

    @api.depends('product_id', 'product_id.seller_ids', 'product_id.seller_ids.delay')
    def _compute_of_supplier_delivery_delay(self):
        for line in self:
            if line.product_id and line.product_id.seller_ids:
                line.of_supplier_delivery_delay = line.product_id.seller_ids[0].delay
            else:
                line.of_supplier_delivery_delay = 0.0

    @api.depends('product_id', 'product_id.nbr_reordering_rules')
    def _compute_of_has_reordering_rule(self):
        for line in self:
            if line.product_id:
                line.of_has_reordering_rule = line.product_id.nbr_reordering_rules > 0

