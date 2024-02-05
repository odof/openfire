# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_analytic_section_id = fields.Many2one(
        comodel_name='of.account.analytic.section', related='procurement_id.sale_line_id.of_analytic_section_id',
        readonly=True
    )
    of_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account', related='procurement_id.sale_line_id.order_id.project_id',
        readonly=True
    )
    of_outlay_analysis_selected = fields.Boolean(
        string=u"Sélectionné", help=u"Sélectionné en produit pour l'analyse des débours", default=True
    )
    of_quant_price_unit = fields.Float(u"Valeur unitaire des quants", compute='_compute_quant_values')
    of_quant_price_total = fields.Float(u"Valeur des quants", compute='_compute_quant_values')

    def _compute_quant_values(self):
        for move in self:
            price = 0.0
            for quant in move.quant_ids:
                if quant.qty < 0:
                    continue
                price += quant.cost * quant.qty
            move.of_quant_price_unit = price / move.product_qty
            move.of_quant_price_total = price
