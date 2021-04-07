# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    of_company_type_id = fields.Many2one(comodel_name='of.res.company.type', string=u"Type de société", readonly=True)
    of_company_sector_id = fields.Many2one(
        comodel_name='of.res.company.sector', string=u"Secteur de société", readonly=True)
    of_company_sales_group_id = fields.Many2one(
        comodel_name='of.res.company.sales.group', string=u"Groupe Ventes de société", readonly=True)

    def _select(self):
        res = super(AccountInvoiceReport, self)._select()
        res += """
            , sub.of_company_type_id        AS of_company_type_id
            , sub.of_company_sector_id      AS of_company_sector_id
            , sub.of_company_sales_group_id AS of_company_sales_group_id
        """
        return res

    def _sub_select(self):
        res = super(AccountInvoiceReport, self)._sub_select()
        res += """
            , RC.of_company_type_id         AS of_company_type_id
            , RC.of_company_sector_id       AS of_company_sector_id
            , RC.of_company_sales_group_id  AS of_company_sales_group_id
        """
        return res

    def _from(self):
        res = super(AccountInvoiceReport, self)._from()
        res += """
            LEFT JOIN res_company RC ON (RC.id = ai.company_id)
        """
        return res

    def _group_by(self):
        res = super(AccountInvoiceReport, self)._group_by()
        res += """
            , RC.of_company_type_id
            , RC.of_company_sector_id
            , RC.of_company_sales_group_id
        """
        return res
