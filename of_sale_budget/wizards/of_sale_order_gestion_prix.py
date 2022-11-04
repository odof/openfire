# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    cost_prorata = fields.Selection(selection_add=[('total_cost', u"Coût total")])


class GestionPrixLine(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix.line'

    def get_base_amount(self, order_line, cost_prorata, all_zero):
        """
        @param order_line: La ligne de commande sur laquelle on récupère les informations
        @param cost_prorata: Le type de prorata utilisé
        @param all_zero: Vrai si cost_prorata == 'cost' et tout les purchase price sont a 0,
                              si cost_prorata == 'price' et tout les price unit sont a 0,
                         Faux dans les autres cas
        """
        if cost_prorata == 'total_cost':
            return order_line.of_total_labor_cost / order_line.product_uom_qty \
                if order_line.product_uom_qty and order_line.of_total_labor_cost else 1.0
        else:
            return super(GestionPrixLine, self).get_base_amount(order_line, cost_prorata, all_zero)
