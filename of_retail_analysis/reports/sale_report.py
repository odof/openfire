# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_company_type_id = fields.Many2one(comodel_name='of.res.company.type', string=u"Type de société", readonly=True)
    of_company_sector_id = fields.Many2one(
        comodel_name='of.res.company.sector', string=u"Secteur de société", readonly=True)
    of_company_sales_group_id = fields.Many2one(
        comodel_name='of.res.company.sales.group', string=u"Groupe Ventes de société", readonly=True)
    of_company_management_group_id = fields.Many2one(
        comodel_name='of.res.company.management.group', string=u"Groupe Gestion de société", readonly=True)

    def _select(self):
        res = super(SaleReport, self)._select()
        res += """
            , RC.of_company_type_id             AS of_company_type_id
            , RC.of_company_sector_id           AS of_company_sector_id
            , RC.of_company_sales_group_id      AS of_company_sales_group_id
            , RC.of_company_management_group_id AS of_company_management_group_id
        """
        return res

    def _from(self):
        res = super(SaleReport, self)._from()
        res += """
            LEFT JOIN res_company RC ON (RC.id = s.company_id)
        """
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += """
            , RC.of_company_type_id
            , RC.of_company_sector_id
            , RC.of_company_sales_group_id
            , RC.of_company_management_group_id
        """
        return res
