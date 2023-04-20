# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

class OFStockHook(models.AbstractModel):
    _name = 'of.stock.hook'

    def _compute_brand_and_category_for_moves(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_stock'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.1.2.0' or False
        if actions_todo:
            cr = self._cr
            # Calcul du champ of_brand_id manuel
            cr.execute("UPDATE stock_move AS sm "
                       "SET of_brand_id = pt.brand_id "
                       "FROM product_product AS pp "
                       "INNER JOIN product_template AS pt ON pt.id=pp.product_tmpl_id "
                       "WHERE sm.product_id = pp.id")
            # Calcul du champ of_categ_id manuel
            cr.execute("UPDATE stock_move AS sm "
                       "SET of_categ_id = pt.categ_id "
                       "FROM product_product AS pp "
                       "INNER JOIN product_template AS pt ON pt.id=pp.product_tmpl_id "
                       "WHERE sm.product_id = pp.id")
