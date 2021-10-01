# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools


class OfInvoicedRevenueAnalysis(models.Model):
    """Analyse CA facturé"""

    _name = 'of.invoiced.revenue.analysis'
    _auto = False
    _description = "Analyse CA facturé"
    _rec_name = 'id'

    date = fields.Date(string=u"Date", readonly=True)

    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    vendor_id = fields.Many2one(comodel_name='res.users', string=u"Vendeur", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire", readonly=True)

    invoiced_total = fields.Float(string=u"CA facturé", readonly=True)
    invoiced_turnover_budget = fields.Float(string=u"Budget CA facturé", readonly=True)
    previous_invoiced_total = fields.Float(string=u"CA facturé N-1", readonly=True)

    invoiced_total_comparison = fields.Char(
        string=u"Comparaison N-1 (%)", compute='_compute_invoiced_total_comparison', compute_sudo=True, readonly=True)
    invoiced_turnover_budget_comparison = fields.Char(
        string=u"Comparaison Budget (%)", compute='_compute_invoiced_turnover_budget_comparison',
        compute_sudo=True, readonly=True)

    @api.multi
    def _compute_invoiced_total_comparison(self):
        for rec in self:
            if rec.previous_invoiced_total != 0:
                rec.invoiced_total_comparison = '%.2f' % (100.0 * rec.invoiced_total / rec.previous_invoiced_total)
            else:
                rec.invoiced_total_comparison = "N/E"

    @api.multi
    def _compute_invoiced_turnover_budget_comparison(self):
        for rec in self:
            if rec.invoiced_turnover_budget != 0:
                rec.invoiced_turnover_budget_comparison = '%.2f' % (100.0 * rec.invoiced_total / rec.invoiced_turnover_budget)
            else:
                rec.invoiced_turnover_budget_comparison = "N/E"

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_invoiced_revenue_analysis')
        self._cr.execute("""
            CREATE VIEW of_invoiced_revenue_analysis AS (
                %s
                FROM
                    (   %s
                        %s
                        %s
                    UNION ALL
                        %s
                        %s
                        %s
                    UNION ALL
                        %s
                        %s
                        %s
                    )           AS T
                %s
                %s
                %s
            )""" % (self._select(),
                    self._sub_select_account_invoice(),
                    self._sub_from_account_invoice(),
                    self._sub_where_account_invoice(),
                    self._sub_select_objective(),
                    self._sub_from_objective(),
                    self._sub_where_objective(),
                    self._sub_select_account_invoice_n_1(),
                    self._sub_from_account_invoice_n_1(),
                    self._sub_where_account_invoice_n_1(),
                    self._from(),
                    self._where(),
                    self._group_by()))

    def _select(self):
        select_str = """
            SELECT      MAX(T.id)                                       AS id
            ,           T.date::date                                    AS date
            ,           T.company_id
            ,           T.vendor_id
            ,           T.partner_id
            ,           SUM(T.invoiced_turnover_budget)                 AS invoiced_turnover_budget
            ,           SUM(T.invoiced_total)                           AS invoiced_total
            ,           SUM(T.previous_invoiced_total)                  AS previous_invoiced_total
        """
        return select_str

    def _sub_select_account_invoice(self):
        sub_select_account_invoice_str = """
            SELECT  AI.id                   AS id
            ,       AI.date_invoice         AS date
            ,       AI.company_id           AS company_id
            ,       AI.user_id              AS vendor_id
            ,       AI.partner_id           AS partner_id
            ,       0                       AS invoiced_turnover_budget
            ,       CASE
                        WHEN AI.type = 'out_invoice' THEN
                            AI.amount_untaxed
                        ELSE
                            -AI.amount_untaxed
                    END                     AS invoiced_total
            ,       0                       AS previous_invoiced_total
        """
        return sub_select_account_invoice_str

    def _sub_from_account_invoice(self):
        sub_from_account_invoice_str = """
            FROM    account_invoice     AI
        """
        return sub_from_account_invoice_str

    def _sub_where_account_invoice(self):
        sub_where_account_invoice_str = """
            WHERE   AI.state           IN ('open', 'paid')
        """
        return sub_where_account_invoice_str

    def _sub_select_objective(self):
        sub_select_objective_str = """
            SELECT  10000000 + OSOL.id                          AS id
            ,       DATE(OSO.year || '-' || OSO.month || '-01') AS date
            ,       OSO.company_id                              AS company_id
            ,       RR.user_id                                  AS vendor_id
            ,       NULL                                        AS partner_id
            ,       OSOL.invoiced_turnover                      AS invoiced_turnover_budget
            ,       0                                           AS invoiced_total
            ,       0                                           AS previous_invoiced_total
        """
        return sub_select_objective_str

    def _sub_from_objective(self):
        sub_from_objective_str = """
            FROM    of_sale_objective       OSO
            ,       of_sale_objective_line  OSOL
            ,       hr_employee             HR
            ,       resource_resource       RR
        """
        return sub_from_objective_str

    def _sub_where_objective(self):
        sub_where_objective_str = """
            WHERE   OSOL.objective_id   = OSO.id
            AND     HR.id               = OSOL.employee_id
            AND     RR.id               = HR.resource_id
        """
        return sub_where_objective_str

    def _sub_select_account_invoice_n_1(self):
        sub_select_account_invoice_n_1_str = """
            SELECT  20000000 + AI.id   AS id
            ,       DATE(
                        EXTRACT(YEAR FROM AI.date_invoice) + 1 || '-' || 
                        TO_CHAR(AI.date_invoice, 'MM') || '-01'
                    )                   AS date
            ,       AI.company_id       AS company_id
            ,       AI.user_id          AS vendor_id
            ,       AI.partner_id       AS partner_id
            ,       0                   AS invoiced_turnover_budget
            ,       0                   AS invoiced_total
            ,       CASE
                        WHEN AI.type = 'out_invoice' THEN
                            AI.amount_untaxed
                        ELSE
                            -AI.amount_untaxed
                    END                 AS previous_invoiced_total
        """
        return sub_select_account_invoice_n_1_str

    def _sub_from_account_invoice_n_1(self):
        sub_from_account_invoice_n_1_str = """
            FROM    account_invoice     AI
        """
        return sub_from_account_invoice_n_1_str

    def _sub_where_account_invoice_n_1(self):
        sub_where_account_invoice_n_1_str = """
            WHERE   AI.state           IN ('open', 'paid')
        """
        return sub_where_account_invoice_n_1_str

    def _from(self):
        from_str = """
        """
        return from_str

    def _where(self):
        where_str = """
        """
        return where_str

    def _group_by(self):
        group_by_str = """
            GROUP BY    T.date
            ,           T.company_id
            ,           T.vendor_id
            ,           T.partner_id
        """
        return group_by_str

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        fields_copy = fields
        if 'invoiced_total' not in fields:
            fields.append('invoiced_total')
        if 'invoiced_turnover_budget' not in fields:
            fields.append('invoiced_turnover_budget')
        if 'previous_invoiced_total' not in fields:
            fields.append('previous_invoiced_total')

        res = super(OfInvoicedRevenueAnalysis, self).read_group(
            domain, fields_copy, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        for line in res:
            if 'invoiced_total_comparison' in fields:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        line.get('previous_invoiced_total', False):
                    line['invoiced_total_comparison'] = ('%.2f' % (round(100.0 * line['invoiced_total'] / line['previous_invoiced_total'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_total_comparison'] = "N/E"
            if 'invoiced_turnover_budget_comparison' in fields:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        line.get('invoiced_turnover_budget', False):
                    line['invoiced_turnover_budget_comparison'] = ('%.2f' % (round(100.0 * line['invoiced_total'] / line['invoiced_turnover_budget'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_turnover_budget_comparison'] = "N/E"

        return res
