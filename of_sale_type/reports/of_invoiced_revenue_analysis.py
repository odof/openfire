# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OfInvoicedRevenueAnalysis(models.Model):
    _inherit = 'of.invoiced.revenue.analysis'

    sale_type_id = fields.Many2one(comodel_name='of.sale.type', string=u"Type de devis", readonly=True)

    def _select(self):
        select_str = super(OfInvoicedRevenueAnalysis, self)._select()
        select_str += ', T.sale_type_id'
        return select_str

    def _sub_select_account_invoice(self):
        sub_select_account_invoice_str = super(OfInvoicedRevenueAnalysis, self)._sub_select_account_invoice()
        sub_select_account_invoice_str += ', AI.of_sale_type_id AS sale_type_id'
        return sub_select_account_invoice_str

    def _sub_select_account_invoice_line(self):
        sub_select_account_invoice_line_str = super(OfInvoicedRevenueAnalysis, self)._sub_select_account_invoice_line()
        sub_select_account_invoice_line_str += ', AI.of_sale_type_id AS sale_type_id'
        return sub_select_account_invoice_line_str

    def _sub_select_objective(self):
        sub_select_objective_str = super(OfInvoicedRevenueAnalysis, self)._sub_select_objective()
        sub_select_objective_str += ', NULL AS sale_type_id'
        return sub_select_objective_str

    def _sub_select_account_invoice_n_1(self):
        sub_select_account_invoice_n_1_str = super(OfInvoicedRevenueAnalysis, self)._sub_select_account_invoice_n_1()
        sub_select_account_invoice_n_1_str += ', AI.of_sale_type_id AS sale_type_id'
        return sub_select_account_invoice_n_1_str

    def _sub_select_sale_order_line(self):
        sub_select_sale_order_line_str = super(OfInvoicedRevenueAnalysis, self)._sub_select_sale_order_line()
        sub_select_sale_order_line_str += ', SO.of_sale_type_id AS sale_type_id'
        return sub_select_sale_order_line_str

    def _sub_select_intervention(self):
        sub_select_intervention_str = super(OfInvoicedRevenueAnalysis, self)._sub_select_intervention()
        sub_select_intervention_str += ', NULL AS sale_type_id'
        return sub_select_intervention_str

    def _sub_select_service(self):
        sub_select_service_str = super(OfInvoicedRevenueAnalysis, self)._sub_select_service()
        sub_select_service_str += ', NULL AS sale_type_id'
        return sub_select_service_str

    def _group_by(self):
        group_by_str = super(OfInvoicedRevenueAnalysis, self)._group_by()
        group_by_str += ', T.sale_type_id'
        return group_by_str
