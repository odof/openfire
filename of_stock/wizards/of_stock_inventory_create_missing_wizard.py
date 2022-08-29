# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFStockInventoryCreateMissingWizard(models.TransientModel):
    _name = 'of.stock.inventory.create.missing.wizard'
    _description = u"Wizard de création des lignes manquantes à 0"

    stock_inventory_id = fields.Many2one(
        comodel_name='stock.inventory', string=u"Inventaire", required=True, ondelete='cascade')
    product_category_ids = fields.Many2many(comodel_name='product.category', string=u"Catégories d'articles")
    all_products = fields.Boolean(string=u"Tous les articles")

    @api.multi
    def create_missing_lines(self):
        self.ensure_one()

        locations = self.env['stock.location'].search([('id', 'child_of', [self.stock_inventory_id.location_id.id])])

        if self.all_products:
            # On prend tous les articles en stock
            self.env.cr.execute(
                """ SELECT      product_id
                    ,           SUM(qty)        AS product_qty
                    ,           location_id
                    ,           lot_id          AS prod_lot_id
                    ,           package_id
                    ,           owner_id        AS partner_id
                    FROM        stock_quant
                    WHERE       location_id     IN %s
                    AND         company_id      = %s
                    GROUP BY    product_id
                    ,           location_id
                    ,           lot_id
                    ,           package_id
                    ,           owner_id
                """, (tuple(locations.ids), self.stock_inventory_id.company_id.id,))
        else:
            # On filtre les articles en stock en fonction des catégories renseignées
            self.env.cr.execute(
                """ SELECT      SQ.product_id
                    ,           SUM(SQ.qty)         AS product_qty
                    ,           SQ.location_id
                    ,           SQ.lot_id           AS prod_lot_id
                    ,           SQ.package_id
                    ,           SQ.owner_id         AS partner_id
                    FROM        stock_quant         SQ
                    ,           product_product     PP
                    ,           product_template    PT
                    WHERE       SQ.location_id      IN %s
                    AND         SQ.company_id       = %s
                    AND         PP.id               = SQ.product_id
                    AND         PT.id               = PP.product_tmpl_id
                    AND         PT.categ_id         IN %s
                    GROUP BY    SQ.product_id
                    ,           SQ.location_id
                    ,           SQ.lot_id
                    ,           SQ.package_id
                    ,           SQ.owner_id
                """, (tuple(locations.ids), self.stock_inventory_id.company_id.id,
                      tuple(self.product_category_ids.ids),))

        data = self.env.cr.dictfetchall()
        vals = []
        product_ids = self.stock_inventory_id.line_ids.mapped('product_id').ids
        prod_lot_ids = self.stock_inventory_id.line_ids.mapped('prod_lot_id').ids
        for product_data in data:
            if product_data['product_qty'] != 0:
                product_data['theoretical_qty'] = product_data['product_qty']
                product_data['product_qty'] = 0.0
                if product_data['product_id'] and product_data['product_id'] not in product_ids:
                    product_data['product_uom_id'] = self.env['product.product'].browse(
                        product_data['product_id']).uom_id.id
                    vals.append(product_data)
                elif product_data['prod_lot_id'] and product_data['product_id'] and \
                        product_data['prod_lot_id'] not in prod_lot_ids:
                    product_data['product_uom_id'] = self.env['product.product'].browse(
                        product_data['product_id']).uom_id.id
                    vals.append(product_data)

        if vals:
            self.stock_inventory_id.write({'line_ids': [(0, 0, line_values) for line_values in vals]})
        return True
