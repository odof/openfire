# -*- coding: utf-8 -*-

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class StockInventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"

    @api.multi
    def _get_inventory_lines_values(self):
        res = super(StockInventory, self)._get_inventory_lines_values()
        for vals in res:
            product = vals.get('product_id') and self.env['product.product'].browse(vals['product_id'])
            uom = vals.get('product_uom_id') and self.env['product.uom'].browse(vals['product_uom_id'])
            if product and uom:
                # On ramène la quantité saisie à l'unité de mesure d'achat
                qty = uom._compute_quantity(1.0, product.uom_po_id)
                vals['product_value_unit'] = product.standard_price * qty
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
    product_value = fields.Monetary(string='Value', digits=dp.get_precision('Product Price'), compute="_compute_product_value")

    @api.depends('product_value_unit', 'product_qty')
    def _compute_product_value(self):
        for line in self:
            line.product_value = line.product_value_unit * line.product_qty

    @api.onchange('product_id', 'product_uom_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_uom_id:
            # On ramène la quantité saisie à l'unité de mesure d'achat
            qty = self.product_uom_id._compute_quantity(1.0, self.product_id.uom_po_id)
            self.product_value_unit = self.product_id.standard_price * qty
        else:
            self.product_value_unit = 0.0


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_picking_min_date = fields.Datetime(compute=lambda x: False, search='_search_of_picking_min_date', string="Date bon de livraison")
    of_picking_date_done = fields.Datetime(compute=lambda x: False, search='_search_of_picking_date_done', string="Date transfert bon de livraison")
    of_route_id = fields.Many2one('stock.location.route', string="Route")

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
            self._cr.execute("SELECT o.id "
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
            self._cr.execute("SELECT o.id "
                "FROM sale_order AS o "
                "INNER JOIN stock_picking AS p ON p.group_id = o.procurement_group_id "
                "WHERE p.id IN %s", (tuple(pickings._ids), ))
            order_ids = [row[0] for row in self._cr.fetchall()]
        return [('id', 'in', order_ids)]


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

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


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_stock_warning_setting = fields.Boolean(string="(OF) Avertissements de stock", required=True, default=False,
            help="Afficher les messages d'avertissement de stock ?")

    @api.multi
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_stock_warning_setting', self.of_stock_warning_setting)

# Ajout configuration "Description articles"
class StockConfiguration(models.TransientModel):
    _inherit = 'stock.config.settings'

    group_description_BL_variant = fields.Selection([
            (0, "Afficher uniquement l'article dans le bon de livraison"),
            (1, "Afficher l'article et sa description dans le bon de livraison")
        ], "(OF) Description articles",
        help = "Choisissez si la description de l'article s'affichée dans le bon de livraison.\nCela affecte également les documents imprimables.",
        implied_group = 'of_sale_stock.group_description_BL_variant')

    @api.multi
    def set_group_description_BL_variant_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'group_description_BL_variant', self.group_description_BL_variant)


# Pour affichage de la contremarque (référence client) du bon de commande client dans le bon de livraison
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    client_order_ref = fields.Char(related="sale_id.client_order_ref")
    of_note_operations = fields.Text('Notes Operations')

    of_purchase_ids = fields.Many2many('purchase.order', compute='_compute_of_purchase_ids', string=u'Achats associés à cette livraison')
    of_purchase_count = fields.Integer('Achats', compute='_compute_of_purchase_ids')

    @api.multi
    def _compute_of_purchase_ids(self):
        purchase_order_obj = self.env['purchase.order']
        for picking in self:
            if picking.sale_id:
                picking.of_purchase_ids = purchase_order_obj.search([('sale_order_id', '=', picking.sale_id.id)])
            elif picking.backorder_id:
                picking.of_purchase_ids = picking.backorder_id.of_purchase_ids
            else:
                picking.of_purchase_ids = []
            picking.of_purchase_count = len(picking.of_purchase_ids)

    @api.multi
    def action_of_view_purchase(self):
        '''
        This function returns an action that display existing purchase orders
        of given delivery ids. It can either be a in a list or in a form
        view, if there is only one purchase order to show.
        '''
        action = self.env.ref('purchase.purchase_form_action').read()[0]

        purchases = self.mapped('of_purchase_ids')
        if len(purchases) > 1:
            action['domain'] = [('id', 'in', purchases._ids)]
        elif purchases:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = purchases.id
        return action

class PackOperation(models.Model):
    _inherit = "stock.pack.operation"

    move_id = fields.Many2one('stock.move', related='linked_move_operation_ids.move_id', string='Move_id')
    move_name = fields.Char(related='move_id.name', string='Description')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_qty_unreserved = fields.Float(string=u'Qté non réservée', compute='_compute_of_qty_unreserved')

    @api.depends('product_variant_ids')
    def _compute_of_qty_unreserved(self):
        quant_obj = self.env['stock.quant']
        for product_template in self:
            products = product_template.mapped('product_variant_ids')
            quants = quant_obj.search([('product_id', 'in', products.ids)]).filtered(lambda q: not q.reservation_id)
            product_template.of_qty_unreserved = sum(quants.mapped('qty'))

