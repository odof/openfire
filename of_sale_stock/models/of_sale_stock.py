# -*- coding: utf-8 -*-

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.addons.stock.models.stock_move import StockMove

from datetime import datetime
from dateutil.relativedelta import relativedelta


@api.multi
def action_assign(self, no_prepare=False):
    """ Checks the product type and accordingly writes the state. """
    # TDE FIXME: remove decorator once everything is migrated
    # TDE FIXME: clean me, please
    main_domain = {}

    Quant = self.env['stock.quant']
    Uom = self.env['product.uom']
    moves_to_assign = self.env['stock.move']
    moves_to_do = self.env['stock.move']
    operations = self.env['stock.pack.operation']
    ancestors_list = {}

    # work only on in progress moves
    moves = self.filtered(lambda move: move.state in ['confirmed', 'waiting', 'assigned'])
    moves.filtered(lambda move: move.reserved_quant_ids).do_unreserve()
    for move in moves:
        if move.location_id.usage in ('supplier', 'inventory', 'production'):
            moves_to_assign |= move
            # TDE FIXME: what ?
            # in case the move is returned, we want to try to find quants before forcing the assignment
            if not move.origin_returned_move_id:
                continue
        # if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
        ancestors = move.find_move_ancestors()
        # OF Modification OpenFire
        if move.product_id.type in ['consu', 'service'] and not ancestors:
            # OF Fin modification OpenFire
            moves_to_assign |= move
            continue
        else:
            moves_to_do |= move

            # we always search for yet unassigned quants
            main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

            ancestors_list[move.id] = True if ancestors else False
            if move.state == 'waiting' and not ancestors:
                # if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available
                # in stock
                main_domain[move.id] += [('id', '=', False)]
            elif ancestors:
                main_domain[move.id] += [('history_ids', 'in', ancestors.ids)]

            # if the move is returned from another, restrict the choice of quants to the ones that follow the returned
            # move
            if move.origin_returned_move_id:
                main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
            for link in move.linked_move_operation_ids:
                operations |= link.operation_id

    # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
    operations = operations.sorted(
        key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (
                x.pack_lot_ids and -1 or 0))
    for ops in operations:
        # TDE FIXME: this code seems to be in action_done, isn't it ? first try to find quants based on specific
        #  domains given by linked operations for the case where we want to rereserve according to existing pack
        #  operations
        if not (ops.product_id and ops.pack_lot_ids):
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                if move.id in main_domain:
                    qty = record.qty
                    domain = main_domain[move.id]
                    if qty:
                        quants = Quant.quants_get_preferred_domain(qty, move, ops=ops, domain=domain,
                                                                   preferred_domain_list=[])
                        Quant.quants_reserve(quants, move, record)
        else:
            lot_qty = {}
            rounding = ops.product_id.uom_id.rounding
            for pack_lot in ops.pack_lot_ids:
                lot_qty[pack_lot.lot_id.id] = ops.product_uom_id._compute_quantity(pack_lot.qty,
                                                                                   ops.product_id.uom_id)
            for record in ops.linked_move_operation_ids:
                move_qty = record.qty
                move = record.move_id
                domain = main_domain[move.id]
                for lot in lot_qty:
                    if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and \
                            float_compare(move_qty, 0, precision_rounding=rounding) > 0:
                        qty = min(lot_qty[lot], move_qty)
                        quants = Quant.quants_get_preferred_domain(qty, move, ops=ops, lot_id=lot, domain=domain,
                                                                   preferred_domain_list=[])
                        Quant.quants_reserve(quants, move, record)
                        lot_qty[lot] -= qty
                        move_qty -= qty

    # Sort moves to reserve first the ones with ancestors, in case the same product is listed in
    # different stock moves.
    for move in sorted(moves_to_do, key=lambda x: -1 if ancestors_list.get(x.id) else 0):
        # then if the move isn't totally assigned, try to find quants without any specific domain
        if move.state != 'assigned' and not self.env.context.get('reserve_only_ops'):
            qty_already_assigned = move.reserved_availability
            qty = move.product_qty - qty_already_assigned

            quants = Quant.quants_get_preferred_domain(qty, move, domain=main_domain[move.id],
                                                       preferred_domain_list=[])
            Quant.quants_reserve(quants, move)

    # force assignation of consumable products and incoming from supplier/inventory/production
    # Do not take force_assign as it would create pack operations
    if moves_to_assign:
        moves_to_assign.write({'state': 'assigned'})
    if not no_prepare:
        self.check_recompute_pack_op()


StockMove.action_assign = action_assign


class StockInventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"

    @api.multi
    def _get_inventory_lines_values(self):
        res = super(StockInventory, self)._get_inventory_lines_values()
        for vals in res:
            product = vals.get('product_id') and self.env['product.product'].browse(vals['product_id'])
            if product:
                vals['product_value_unit'] = product.standard_price
        return res


class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    @api.model_cr_context
    def _auto_init(self):
        # Initialise la valeur des lignes d'inventaire déjà existantes en base de données
        self._cr.execute("SELECT * FROM information_schema.columns "
                         "WHERE table_name = 'stock_inventory_line' AND column_name = 'product_value_unit'")
        set_value = not self._cr.fetchall()
        super(StockInventoryLine, self)._auto_init()
        if set_value:
            for inv in self.sudo().env['stock.inventory'].search([]):
                inv = inv.with_context(force_company=inv.company_id.id)
                for line in inv.line_ids:
                    line._onchange_product_id()

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related="company_id.currency_id")
    product_value_unit = fields.Monetary(string='Valeur unitaire', digits=dp.get_precision('Product Price'))
    product_value = fields.Monetary(
        string='Value', digits=dp.get_precision('Product Price'), compute="_compute_product_value")

    @api.depends('product_value_unit', 'product_qty')
    def _compute_product_value(self):
        if self.env.user.has_group('of_sale_stock.group_of_inventory_real_value'):
            if not self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire'):
                for line in self:
                    line.product_value = sum([x.qty * x.cost for x in line._get_quants()])
            else:
                for line in self:
                    line.product_value = line.of_get_stock_history()[1]
        else:
            for line in self:
                line.product_value = line.product_value_unit * line.product_qty

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_value_unit = self.product_id.standard_price
        else:
            self.product_value_unit = 0.0


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
                        (datetime.today() + relativedelta(days=orderpoints.of_forecast_period)).\
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


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_stock_warning_setting = fields.Boolean(
        string="(OF) Avertissements de stock", required=True, default=False,
        help="Afficher les messages d'avertissement de stock ?")

    default_invoice_policy = fields.Selection(
        selection_add=[('ordered_delivery', u"Facturer les quantités commandées à date de livraison")])
    group_sale_order_line_display_stock_info = fields.Boolean(
        string=u"(OF) Informations de stock",
        implied_group='of_sale_stock.group_sale_order_line_display_stock_info',
        group='base.group_portal,base.group_user,base.group_public',
        help=u"Affiche les informations de stock au niveau des lignes de commande")
    group_sale_order_line_display_menu_info = fields.Boolean(
            string=u"(OF) Menu lignes de commande",
            implied_group='of_sale_stock.group_sale_order_line_display_menu_info',
            group='base.group_portal,base.group_user,base.group_public',
            help=u"Affiche le menu lignes de commande depuis le menu ventes")
    of_inclure_service_bl = fields.Boolean(
        string="(OF) Bons de Livraison", help=u"Inclure les articles de type 'service' dans les bons de livraison"
        )

    @api.multi
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_stock_warning_setting', self.of_stock_warning_setting)

    @api.multi
    def set_of_inclure_service_bl(self):
        return self.env['ir.values'].sudo().set_default(
                'sale.config.settings', 'of_inclure_service_bl', self.of_inclure_service_bl)


# Ajout configuration "Description articles"
class StockConfiguration(models.TransientModel):
    _inherit = 'stock.config.settings'

    group_description_BL_variant = fields.Selection(
        [
            (0, "Afficher uniquement l'article dans le bon de livraison"),
            (1, "Afficher l'article et sa description dans le bon de livraison")
            ], "(OF) Description articles",
        help=u"Choisissez si la description de l'article s'affichée dans le bon de livraison.\n"
             u"Cela affecte également les documents imprimables.",
        implied_group='of_sale_stock.group_description_BL_variant')
    group_of_inventory_real_value = fields.Selection(
        selection=[(0, u"Prix de revient de l'article"), (1, u"Valeur réelle des mouvements (Quants)")],
        string=u"(OF) Méthode de valorisation de l'inventaire",
        implied_group='of_sale_stock.group_of_inventory_real_value')

    @api.multi
    def set_group_description_BL_variant_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'group_description_BL_variant', self.group_description_BL_variant)


# Pour affichage de la contremarque (référence client) du bon de commande client dans le bon de livraison
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    client_order_ref = fields.Char(related="sale_id.client_order_ref")
    of_note_operations = fields.Text('Notes Operations')

    of_purchase_ids = fields.Many2many(
        'purchase.order', compute='_compute_of_purchase_ids', string=u'Achats associés à cette livraison')
    of_purchase_count = fields.Integer('Achats', compute='_compute_of_purchase_ids')

    of_min_week = fields.Char(string=u"Semaine prévue", compute='_compute_of_min_week', store=True)

    @api.multi
    def _compute_of_purchase_ids(self):
        purchase_order_obj = self.env['purchase.order']
        for picking in self:
            purchases = purchase_order_obj
            if picking.sale_id:
                purchases |= purchase_order_obj.search([('sale_order_id', '=', picking.sale_id.id)])
            if picking.backorder_id:
                purchases |= picking.backorder_id.of_purchase_ids
            purchases |= self.env['procurement.order'].search([('move_dest_id.picking_id', '=', picking.id)])\
                .mapped('purchase_line_id').mapped('order_id')
            picking.of_purchase_ids = purchases.ids
            picking.of_purchase_count = len(picking.of_purchase_ids)

    @api.multi
    def action_of_view_purchase(self):
        """
        This function returns an action that display existing purchase orders
        of given delivery ids. It can either be a in a list or in a form
        view, if there is only one purchase order to show.
        """
        action = self.env.ref('purchase.purchase_form_action').read()[0]

        purchases = self.mapped('of_purchase_ids')
        if len(purchases) > 1:
            action['domain'] = [('id', 'in', purchases._ids)]
        elif purchases:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = purchases.id
        return action

    @api.multi
    def action_delivery_division(self):
        self.ensure_one()

        line_vals = []
        for line in self.move_lines:
            line_vals.append((0, 0, {'move_id': line.id}))

        wizard = self.env['of.delivery.division.wizard'].create({
            'picking_id': self.id,
            'line_ids': line_vals,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': "Division du bon de transfert",
            'view_mode': 'form',
            'res_model': 'of.delivery.division.wizard',
            'res_id': wizard.id,
            'target': 'new',
            }

    @api.depends('move_lines.date_expected')
    def _compute_of_min_week(self):
        for picking in self:
            min_date = min(picking.move_lines.mapped('date_expected') or [False])
            if min_date:
                min_year = fields.Date.from_string(min_date).year
                min_week = datetime.strptime(min_date, "%Y-%m-%d %H:%M:%S").date().isocalendar()[1]
                picking.of_min_week = "%s - S%02d" % (min_year, min_week)
            else:
                picking.of_min_week = ""

    @api.multi
    def get_sale_value(self):
        self.ensure_one()

        amount = 0.0
        kit_line_ids = []
        for line in self.move_lines:
            if line.procurement_id.sale_line_id:
                amount += line.procurement_id.sale_line_id.of_price_unit_ttc * line.product_uom_qty
            elif line.procurement_id.of_sale_comp_id and \
                    line.procurement_id.of_sale_comp_id.kit_id.order_line_id.id not in kit_line_ids:
                amount += line.procurement_id.of_sale_comp_id.kit_id.order_line_id.price_total
                kit_line_ids.append(line.procurement_id.of_sale_comp_id.kit_id.order_line_id.id)

        if amount:
            order = self.move_lines.mapped('procurement_id').mapped('sale_line_id').mapped('order_id')
            if order:
                currency = order[0].currency_id
            else:
                currency = self.move_lines.mapped('procurement_id').mapped('of_sale_comp_id').mapped('kit_id').\
                    mapped('order_line_id').mapped('order_id')[0].currency_id
            return currency.round(amount)
        return amount


class PackOperation(models.Model):
    _inherit = "stock.pack.operation"

    move_id = fields.Many2one('stock.move', related='linked_move_operation_ids.move_id', string='Move_id')
    move_name = fields.Char(related='move_id.name', string='Description')
    move_state = fields.Selection(related='move_id.state', string=u"État")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_qty_unreserved = fields.Float(string=u'Qté non réservée', compute='_compute_of_qty_unreserved')

    invoice_policy = fields.Selection(selection_add=[('ordered_delivery', u'Quantités commandées à date de livraison')])

    @api.depends('product_variant_ids')
    def _compute_of_qty_unreserved(self):
        quant_obj = self.env['stock.quant']
        for product_template in self:
            products = product_template.mapped('product_variant_ids')
            quants = quant_obj.search([('product_id', 'in', products.ids)]).filtered(lambda q: not q.reservation_id)
            product_template.of_qty_unreserved = sum(quants.mapped('qty'))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _need_procurement(self):
        inclure_service = self.env['ir.values'].get_default('sale.config.settings', 'of_inclure_service_bl')
        for product in self:
            if inclure_service and product.type == 'service':
                return True
        return super(ProductProduct, self)._need_procurement()


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _assign(self):
        res = super(ProcurementOrder, self)._assign()
        if not res and self.product_id.type == 'service':
            rule = self._find_suitable_rule()
            if rule:
                self.write({'rule_id': rule.id})
                return True
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_ordered_qty = fields.Float(string=u"(OF) Quantité commandée", digits=dp.get_precision('Product Unit of Measure'))

    @api.model
    def create(self, vals):
        vals['of_ordered_qty'] = vals.get('product_uom_qty')
        if vals.get('split_from'):
            origin_move = self.browse(vals.get('split_from'))
            origin_move.of_ordered_qty = origin_move.of_ordered_qty - vals['of_ordered_qty']
        return super(StockMove, self).create(vals)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_invoice_policy = fields.Selection(
        selection_add=[('ordered_delivery', u'Quantités commandées à date de livraison')])
    of_sale_order_lines_count = fields.Integer(
        string=u"Nombre de lignes de commande", compute='_compute_of_sale_order_lines_count')

    @api.multi
    def _compute_of_sale_order_lines_count(self):
        for partner in self:
            partner.of_sale_order_lines_count = len(self.env['sale.order.line'].search(
                [('order_partner_id', 'child_of', partner.id)]))

    @api.multi
    def action_view_sale_order_lines(self):
        self.ensure_one()
        action = self.env.ref('of_sale_stock.of_sale_stock_sale_order_line_action').read()[0]
        action['domain'] = [('order_partner_id', 'child_of', self.id)]
        return action
