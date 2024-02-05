# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res['of_analytic_section_id'] = self.of_analytic_section_id
        return res
