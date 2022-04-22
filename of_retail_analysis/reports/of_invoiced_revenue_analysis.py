# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools


class OfInvoicedRevenueAnalysis(models.Model):
    """Analyse CA facturé"""

    _inherit = 'of.invoiced.revenue.analysis'

    company_type_id = fields.Many2one(
        comodel_name='of.res.company.type', string=u"Type de société", readonly=True)
    company_sector_id = fields.Many2one(
        comodel_name='of.res.company.sector', string=u"Secteur de société", readonly=True)
    company_sales_group_id = fields.Many2one(
        comodel_name='of.res.company.sales.group', string=u"Groupe Ventes de société", readonly=True)
    company_management_group_id = fields.Many2one(
        comodel_name='of.res.company.management.group', string=u"Groupe Gestion de société", readonly=True)

    def _select(self):
        select_str = super(OfInvoicedRevenueAnalysis, self)._select()
        select_str += """
            ,           RC.of_company_type_id                           AS company_type_id
            ,           RC.of_company_sector_id                         AS company_sector_id
            ,           RC.of_company_sales_group_id                    AS company_sales_group_id
            ,           RC.of_company_management_group_id               AS company_management_group_id
        """
        return select_str

    def _from(self):
        from_str = super(OfInvoicedRevenueAnalysis, self)._from()
        from_str += """
            ,   res_company AS RC
        """
        return from_str

    def _where(self):
        where_str = super(OfInvoicedRevenueAnalysis, self)._where()
        where_str += """
            WHERE   RC.id   = T.company_id
        """
        return where_str

    def _group_by(self):
        group_by_str = super(OfInvoicedRevenueAnalysis, self)._group_by()
        group_by_str += """
            ,           RC.of_company_type_id
            ,           RC.of_company_sector_id
            ,           RC.of_company_sales_group_id
            ,           RC.of_company_management_group_id
        """
        return group_by_str
