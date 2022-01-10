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
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", readonly=True)
    product_categ_id = fields.Many2one(comodel_name='product.category', string=u"Catégorie de l'article", readonly=True)
    product_brand_id = fields.Many2one(comodel_name='of.product.brand', string=u"Marque de l'article", readonly=True)

    invoiced_total = fields.Float(string=u"CA facturé", readonly=True)
    residual = fields.Float(string=u"Montant dû (€)", readonly=True)
    invoiced_turnover_budget = fields.Float(string=u"Budget CA facturé", readonly=True)
    previous_invoiced_total = fields.Float(string=u"CA facturé N-1", readonly=True)
    amount_to_invoice = fields.Float(string=u"CA à facturer prévisionnel", readonly=True)

    margin_total = fields.Float(string=u"Marge facturé", readonly=True)
    margin_perc = fields.Char(
        string=u"Marge facturé (%)", compute='_compute_margin_perc', compute_sudo=True, readonly=True)

    invoiced_turnover_budget_gap = fields.Char(
        string=u"Écart au budget (€)", compute='_compute_invoiced_turnover_budget_gap',
        compute_sudo=True, readonly=True)

    invoiced_total_comparison = fields.Char(
        string=u"Comparaison N-1 (%)", compute='_compute_invoiced_total_comparison', compute_sudo=True, readonly=True)
    invoiced_turnover_budget_comparison = fields.Char(
        string=u"Comparaison Budget (%)", compute='_compute_invoiced_turnover_budget_comparison',
        compute_sudo=True, readonly=True)

    @api.multi
    def _compute_margin_perc(self):
        for rec in self:
            if rec.invoiced_total != 0:
                rec.margin_perc = '%.2f' % (100.0 * rec.margin_total / rec.invoiced_total)
            else:
                rec.margin_perc = "N/E"

    @api.multi
    def _compute_invoiced_turnover_budget_gap(self):
        for rec in self:
            rec.invoiced_turnover_budget_gap = \
                '%.2f' % ((rec.invoiced_total + rec.amount_to_invoice) - rec.invoiced_turnover_budget)

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
                rec.invoiced_turnover_budget_comparison = '%.2f' % \
                    (100.0 * rec.invoiced_total / rec.invoiced_turnover_budget)
            else:
                rec.invoiced_turnover_budget_comparison = "N/E"

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_invoiced_revenue_analysis')
        self._cr.execute("""
            CREATE VIEW of_invoiced_revenue_analysis AS (
                %s
                %s
                %s
                %s
            )""" % (self._select(),
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
            ,           T.product_id
            ,           T.product_categ_id
            ,           T.product_brand_id
            ,           SUM(T.invoiced_turnover_budget)                 AS invoiced_turnover_budget
            ,           SUM(T.invoiced_total)                           AS invoiced_total
            ,           SUM(T.previous_invoiced_total)                  AS previous_invoiced_total
            ,           SUM(T.margin_total)                             AS margin_total
            ,           SUM(T.amount_to_invoice)                        AS amount_to_invoice
            ,           SUM(T.residual)                                 AS residual
        """
        return select_str

    def _from(self):
        from_str = """
            FROM    (%s) AS T
        """ % self._sub_from()
        return from_str

    def _sub_from(self):
        sub_from_str = """
            %s
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
        UNION ALL
            %s
            %s
            %s
        UNION ALL
            %s
            %s
            %s
        """ % (self._sub_select_account_invoice(),
               self._sub_from_account_invoice(),
               self._sub_where_account_invoice(),
               self._sub_select_account_invoice_line(),
               self._sub_from_account_invoice_line(),
               self._sub_where_account_invoice_line(),
               self._sub_select_objective(),
               self._sub_from_objective(),
               self._sub_where_objective(),
               self._sub_select_account_invoice_n_1(),
               self._sub_from_account_invoice_n_1(),
               self._sub_where_account_invoice_n_1(),
               self._sub_select_sale_order_line(),
               self._sub_from_sale_order_line(),
               self._sub_where_sale_order_line())
        return sub_from_str

    def _sub_select_account_invoice(self):
        sub_select_account_invoice_str = """
            SELECT  AI.id                                       AS id
            ,       GREATEST(AI.date_invoice, CURRENT_DATE)     AS date
            ,       AI.company_id                               AS company_id
            ,       AI.user_id                                  AS vendor_id
            ,       AI.partner_id                               AS partner_id
            ,       NULL                                        AS product_id
            ,       NULL                                        AS product_categ_id
            ,       NULL                                        AS product_brand_id
            ,       0                                           AS invoiced_turnover_budget
            ,       0                                           AS invoiced_total
            ,       0                                           AS previous_invoiced_total
            ,       0                                           AS margin_total
            ,       0                                           AS amount_to_invoice
            ,       AI.residual_signed                          AS residual
        """
        return sub_select_account_invoice_str

    def _sub_from_account_invoice(self):
        sub_from_account_invoice_str = """
            FROM    account_invoice         AI
        """
        return sub_from_account_invoice_str

    def _sub_where_account_invoice(self):
        sub_where_account_invoice_str = """
            WHERE   AI.state            = 'open'
            AND     AI.type             IN ('out_invoice', 'out_refund')
        """
        return sub_where_account_invoice_str

    def _sub_select_account_invoice_line(self):
        sub_select_account_invoice_line_str = """
            SELECT  10000000 + AIL.id       AS id
            ,       AI.date_invoice         AS date
            ,       AI.company_id           AS company_id
            ,       AI.user_id              AS vendor_id
            ,       AI.partner_id           AS partner_id
            ,       PP.id                   AS product_id
            ,       PT.categ_id             AS product_categ_id
            ,       PT.brand_id             AS product_brand_id
            ,       0                       AS invoiced_turnover_budget
            ,       CASE
                        WHEN AI.type = 'out_invoice' THEN
                            AIL.price_subtotal
                        ELSE
                            -AIL.price_subtotal
                    END                     AS invoiced_total
            ,       0                       AS previous_invoiced_total
            ,       AIL.of_margin           AS margin_total
            ,       0                       AS amount_to_invoice
            ,       0                       AS residual
        """
        return sub_select_account_invoice_line_str

    def _sub_from_account_invoice_line(self):
        sub_from_account_invoice_line_str = """
            FROM    account_invoice         AI
            ,       account_invoice_line    AIL
            ,       product_product         PP
            ,       product_template        PT
        """
        return sub_from_account_invoice_line_str

    def _sub_where_account_invoice_line(self):
        sub_where_account_invoice_line_str = """
            WHERE   AI.state            IN ('open', 'paid')
            AND     AI.type             IN ('out_invoice', 'out_refund')
            AND     AI.id               = AIL.invoice_id
            AND     PP.id               = AIL.product_id
            AND     PP.product_tmpl_id  = PT.id
        """
        return sub_where_account_invoice_line_str

    def _sub_select_objective(self):
        sub_select_objective_str = """
            SELECT  20000000 + OSOL.id                          AS id
            ,       DATE(OSO.year || '-' || OSO.month || '-01') AS date
            ,       OSO.company_id                              AS company_id
            ,       RR.user_id                                  AS vendor_id
            ,       NULL                                        AS partner_id
            ,       NULL                                        AS product_id
            ,       NULL                                        AS product_categ_id
            ,       NULL                                        AS product_brand_id
            ,       OSOL.invoiced_turnover                      AS invoiced_turnover_budget
            ,       0                                           AS invoiced_total
            ,       0                                           AS previous_invoiced_total
            ,       0                                           AS margin_total
            ,       0                                           AS amount_to_invoice
            ,       0                                           AS residual
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
            SELECT  30000000 + AI.id    AS id
            ,       DATE(
                        EXTRACT(YEAR FROM AI.date_invoice) + 1 || '-' || 
                        TO_CHAR(AI.date_invoice, 'MM') || '-01'
                    )                   AS date
            ,       AI.company_id       AS company_id
            ,       AI.user_id          AS vendor_id
            ,       AI.partner_id       AS partner_id
            ,       NULL                AS product_id
            ,       NULL                AS product_categ_id
            ,       NULL                AS product_brand_id
            ,       0                   AS invoiced_turnover_budget
            ,       0                   AS invoiced_total
            ,       CASE
                        WHEN AI.type = 'out_invoice' THEN
                            AI.amount_untaxed
                        ELSE
                            -AI.amount_untaxed
                    END                 AS previous_invoiced_total
            ,       0                   AS margin_total
            ,       0                   AS amount_to_invoice
            ,       0                   AS residual
        """
        return sub_select_account_invoice_n_1_str

    def _sub_from_account_invoice_n_1(self):
        sub_from_account_invoice_n_1_str = """
            FROM    account_invoice         AI
        """
        return sub_from_account_invoice_n_1_str

    def _sub_where_account_invoice_n_1(self):
        sub_where_account_invoice_n_1_str = """
            WHERE   AI.state           IN ('open', 'paid')
        """
        return sub_where_account_invoice_n_1_str

    def _sub_select_sale_order_line(self):
        sub_select_sale_order_line_str = """
            SELECT  40000000 + SOL.id                                               AS id
            ,       CASE
                        WHEN SOL.state = 'presale' THEN
                            SO.of_date_de_pose
                        WHEN SOL.product_id = ( SELECT  PP2.id
                                                FROM    ir_values                   IV
                                                ,       product_template            PT2
                                                ,       product_product             PP2
                                                WHERE   IV.name                     = 'of_deposit_product_categ_id_setting'
                                                AND     PT2.categ_id                = SUBSTR(value, 2, POSITION(E'\n' in value) - 1)::INT
                                                AND     PT2.type                    = 'service'
                                                AND     PP2.product_tmpl_id         = PT2.id
                                                LIMIT   1
                                               )
                        THEN
                            (   SELECT  MAX(SOL2.of_invoice_date_prev)
                                FROM    sale_order_line                 SOL2
                                WHERE   SOL2.order_id                   = SOL.order_id
                            )
                        WHEN SOL.of_invoice_policy = 'order' THEN
                            CURRENT_DATE
                        ELSE
                            SOL.of_invoice_date_prev
                    END                                                             AS date
            ,       SO.company_id                                                   AS company_id
            ,       SO.user_id                                                      AS vendor_id
            ,       SO.partner_id                                                   AS partner_id
            ,       PP.id                                                           AS product_id
            ,       PT.categ_id                                                     AS product_categ_id
            ,       PT.brand_id                                                     AS product_brand_id
            ,       0                                                               AS invoiced_turnover_budget
            ,       0                                                               AS invoiced_total
            ,       0                                                               AS previous_invoiced_total
            ,       0                                                               AS margin_total
            ,       SOL.of_amount_to_invoice                                        AS amount_to_invoice
            ,       0                                                               AS residual
        """
        return sub_select_sale_order_line_str

    def _sub_from_sale_order_line(self):
        sub_from_sale_order_line_str = """
            FROM    sale_order          SO
            ,       sale_order_line     SOL
            ,       product_product     PP
            ,       product_template    PT
        """
        return sub_from_sale_order_line_str

    def _sub_where_sale_order_line(self):
        sub_where_sale_order_line_str = """
            WHERE   SOL.invoice_status          IN ('no', 'to invoice')
            AND     SOL.of_amount_to_invoice    != 0
            AND     SO.id                       = SOL.order_id
            AND     SO.state                    NOT IN ('draft', 'sent', 'closed', 'cancel')
            AND     PP.id                       = SOL.product_id
            AND     PP.product_tmpl_id          = PT.id
        """
        return sub_where_sale_order_line_str

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
            ,           T.product_id
            ,           T.product_categ_id
            ,           T.product_brand_id
        """
        return group_by_str

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'invoiced_total' not in fields:
            fields.append('invoiced_total')
        if 'invoiced_turnover_budget' not in fields:
            fields.append('invoiced_turnover_budget')
        if 'previous_invoiced_total' not in fields:
            fields.append('previous_invoiced_total')
        if 'amount_to_invoice' not in fields:
            fields.append('amount_to_invoice')
        if 'margin_total' not in fields:
            fields.append('margin_total')

        res = super(OfInvoicedRevenueAnalysis, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        for line in res:
            if 'margin_perc' in fields:
                if 'margin_total' in line and line['margin_total'] is not None and line.get('invoiced_total', False):
                    line['margin_perc'] = \
                        ('%.2f' % (round(100.0 * line['margin_total'] / line['invoiced_total'], 2))).\
                        replace('.', ',')
                else:
                    line['margin_perc'] = "N/E"
            if 'invoiced_turnover_budget_gap' in fields:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        'amount_to_invoice' in line and line['amount_to_invoice'] is not None and \
                        'invoiced_turnover_budget' in line and line['invoiced_turnover_budget'] is not None:
                    value = (line['invoiced_total'] + line['amount_to_invoice']) - line['invoiced_turnover_budget']
                    line['invoiced_turnover_budget_gap'] = '{:,.2f}'.format(value).replace(',', ' ').replace('.', ',')
                else:
                    line['invoiced_turnover_budget_gap'] = "N/E"
            if 'invoiced_total_comparison' in fields:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        line.get('previous_invoiced_total', False):
                    line['invoiced_total_comparison'] = \
                        ('%.2f' % (round(100.0 * line['invoiced_total'] / line['previous_invoiced_total'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_total_comparison'] = "N/E"
            if 'invoiced_turnover_budget_comparison' in fields:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        line.get('invoiced_turnover_budget', False):
                    line['invoiced_turnover_budget_comparison'] = \
                        ('%.2f' % (round(100.0 * line['invoiced_total'] / line['invoiced_turnover_budget'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_turnover_budget_comparison'] = "N/E"

        return res
