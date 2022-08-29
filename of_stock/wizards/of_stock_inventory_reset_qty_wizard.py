# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFStockInventoryResetQtyWizard(models.TransientModel):
    _name = 'of.stock.inventory.reset.qty.wizard'
    _description = u"Wizard de remise à zéro des quantités inventaire"

    stock_inventory_id = fields.Many2one(
        comodel_name='stock.inventory', string=u"Inventaire", required=True, ondelete='cascade')
    product_category_ids = fields.Many2many(
        comodel_name='product.category', string=u"Catégories d'articles", required=True)

    @api.multi
    def reset_real_qty_category(self):
        # On ne remet les quantités à 0 que pour les catégories sélectionnées
        self.stock_inventory_id.line_ids.filtered(
            lambda l: l.product_id.categ_id in self.product_category_ids).write({'product_qty': 0})
        return True
