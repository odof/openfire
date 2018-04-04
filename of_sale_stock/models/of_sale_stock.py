# -*- coding: utf-8 -*-

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class OFSaleStockInventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"


class OFSaleStockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related="company_id.currency_id")
    product_value = fields.Monetary('Value', digits=dp.get_precision('Product Price'), compute="_compute_product_value")

    @api.multi
    @api.depends('product_id.standard_price', 'product_qty')
    def _compute_product_value(self):
        for line in self:
            # @TODO: ajouter un paramètre config pour choisir la façon de calculer la valeur
            # @TODO: gérer le multi-currency
            if line.product_id:
                line.product_value = line.product_id.standard_price * line.product_qty
            else:
                line.product_value = 0.0


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_picking_min_date = fields.Datetime(compute=lambda x: False, search='_search_of_picking_min_date', string="Date bon de livraison")
    of_picking_date_done = fields.Datetime(compute=lambda x: False, search='_search_of_picking_date_done', string="Date transfert bon de livraison")

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


class OFSaleStockSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        # Inhiber la vérification de stock
        afficher_warning = self.env['ir.values'].get_default('sale.config.settings', 'of_stock_warning_setting')
        if afficher_warning:
            return super(OFSaleStockSaleOrderLine, self)._onchange_product_id_check_availability()


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_stock_warning_setting = fields.Boolean(string="(OF) Avertissements de stock", required=True, default=False,
            help="Afficher les messages d'avertissement de stock ?")

    @api.multi
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_stock_warning_setting', self.of_stock_warning_setting)

# Ajout configuration "Description articles"
class OFStockConfiguration(models.TransientModel):
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


class PackOperation(models.Model):
    _inherit = "stock.pack.operation"

    move_id = fields.Many2one('stock.move', related='linked_move_operation_ids.move_id', string='Move_id')
    move_name = fields.Char(related='move_id.name', string='Description')
