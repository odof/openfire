# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp


class OfSaleOrderKanban(models.Model):
    _name = 'of.sale.order.kanban'
    _description = u"Étapes kanban des sale.order"

    name = fields.Char(string=u"Nom de l'étape", required=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_kanban_step_id = fields.Many2one(
        comodel_name='of.sale.order.kanban', string=u"Étape kanban",
        default=lambda s: s.env.ref('of_sale.of_sale_order_kanban_new', raise_if_not_found=False)
    )

    @api.model
    def function_set_kanban_step_id(self):
        step = self.env.ref('of_sale.of_sale_order_kanban_new', raise_if_not_found=False)
        if step:
            self._cr.execute('UPDATE sale_order SET of_kanban_step_id = %s', (step.id,))

