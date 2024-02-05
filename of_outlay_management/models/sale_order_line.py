# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")
    of_outlay_analysis_selected = fields.Boolean(
        string=u"Sélectionné", help=u"Sélectionné en produit pour l'analyse des débours", default=True
    )
    of_outlay_analysis_cost_selected = fields.Boolean(
        string=u"Sélectionné", help=u"Sélectionné en charge pour l'analyse des débours", default=True
    )
    of_outlay_analysis_type = fields.Selection(related='order_id.of_outlay_analysis_type')
    of_order_project_id = fields.Many2one(comodel_name='account.analytic.account', related='order_id.project_id')
    of_purchase_price_subtotal = fields.Float(
        string=u"Prix d'achat total", compute='_compute_of_purchase_price_subtotal')

    @api.depends('purchase_price', 'product_uom_qty')
    def _compute_of_purchase_price_subtotal(self):
        for line in self:
            line.of_purchase_price_subtotal = line.currency_id.round(line.purchase_price * line.product_uom_qty)

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res['of_analytic_section_id'] = self.of_analytic_section_id
        return res
