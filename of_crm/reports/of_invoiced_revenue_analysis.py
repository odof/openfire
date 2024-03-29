# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, tools, _


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

    amount_to_invoice_intervention = fields.Float(string=u"Reste à facturer planifié", readonly=True)
    amount_to_invoice_service = fields.Float(string=u"Reste à facturer non planifié", readonly=True)

    margin_total = fields.Float(string=u"Marge facturé", readonly=True)
    margin_perc = fields.Char(
        string=u"Marge facturé (%)", compute='_compute_margin_perc', compute_sudo=True, readonly=True)

    landing_forecast_sales = fields.Char(
        string=u"Atterrissage CA prévisionnel", compute='_compute_landing_forecast_sales', compute_sudo=True,
        readonly=True)

    invoiced_turnover_budget_gap = fields.Char(
        string=u"Écart au budget (€)", compute='_compute_invoiced_turnover_budget_gap',
        compute_sudo=True, readonly=True)

    invoiced_total_comparison = fields.Char(
        string=u"Comparaison N-1 (%)", compute='_compute_invoiced_total_comparison', compute_sudo=True, readonly=True)
    invoiced_turnover_budget_comparison = fields.Char(
        string=u"Comparaison Budget (%)", compute='_compute_invoiced_turnover_budget_comparison',
        compute_sudo=True, readonly=True)

    my_company = fields.Boolean(
        string=u"Est mon magasin ?", compute='_get_is_my_company', search='_search_is_my_company')

    @api.model
    def _search_is_my_company(self, operator, value):
        if operator != '=' or not value:
            raise ValueError(_("Unsupported search operator"))
        return [('company_id', '=', self.env.user.company_id.id)]

    def _get_is_my_company(self):
        for rec in self:
            rec.my_company = self.env.user.company_id == rec.company_id

    @api.multi
    def _compute_margin_perc(self):
        for rec in self:
            if rec.invoiced_total != 0:
                rec.margin_perc = '%.2f' % (100.0 * rec.margin_total / rec.invoiced_total)
            else:
                rec.margin_perc = "N/E"

    @api.multi
    def _compute_landing_forecast_sales(self):
        for rec in self:
            rec.landing_forecast_sales = rec.invoiced_total + rec.amount_to_invoice + rec.amount_to_invoice_intervention

    @api.multi
    def _compute_invoiced_turnover_budget_gap(self):
        for rec in self:
            rec.invoiced_turnover_budget_gap = \
                '%.0f' % ((rec.invoiced_total + rec.amount_to_invoice + rec.amount_to_invoice_intervention)
                          - rec.invoiced_turnover_budget)

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
        # On récupère l'article acompte
        product_id = None
        categ_id = self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting')
        if categ_id:
            product = self.env['product.product'].search(
                [('categ_id', '=', categ_id), ('type', '=', 'service')], limit=1)
            if product:
                product_id = product.id

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
                    self._group_by()),
            (product_id, ))

    def _select(self):
        select_str = """
            SELECT      MAX(T.id)                                       AS id
            ,           T.date::date                                    AS date
            ,           T.company_id
            ,           T.vendor_id
            ,           T.partner_id
            ,           T.product_id
            ,           PT.categ_id                                     AS product_categ_id
            ,           PT.brand_id                                     AS product_brand_id
            ,           SUM(T.invoiced_turnover_budget)                 AS invoiced_turnover_budget
            ,           SUM(T.invoiced_total)                           AS invoiced_total
            ,           SUM(T.previous_invoiced_total)                  AS previous_invoiced_total
            ,           SUM(T.margin_total)                             AS margin_total
            ,           SUM(T.amount_to_invoice)                        AS amount_to_invoice
            ,           SUM(T.amount_to_invoice_intervention)           AS amount_to_invoice_intervention
            ,           SUM(T.amount_to_invoice_service)                AS amount_to_invoice_service
            ,           SUM(T.residual)                                 AS residual
        """
        return select_str

    def _from(self):
        from_str = """
            FROM    (%s)                        AS T
            LEFT JOIN product_product           AS PP
                ON PP.id = T.product_id
            LEFT JOIN product_template          AS PT
                ON PT.id = PP.product_tmpl_id
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
               self._sub_where_sale_order_line(),
               self._sub_select_intervention(),
               self._sub_from_intervention(),
               self._sub_where_intervention(),
               self._sub_select_service(),
               self._sub_from_service(),
               self._sub_where_service())
        return sub_from_str

    def _sub_select_account_invoice(self):
        sub_select_account_invoice_str = """
            SELECT  AI.id                                       AS id
            ,       GREATEST(AI.date_invoice, CURRENT_DATE)     AS date
            ,       AI.company_id                               AS company_id
            ,       AI.user_id                                  AS vendor_id
            ,       AI.partner_id                               AS partner_id
            ,       NULL                                        AS product_id
            ,       0                                           AS invoiced_turnover_budget
            ,       0                                           AS invoiced_total
            ,       0                                           AS previous_invoiced_total
            ,       0                                           AS margin_total
            ,       0                                           AS amount_to_invoice
            ,       0                                           AS amount_to_invoice_intervention
            ,       0                                           AS amount_to_invoice_service
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
            ,       AIL.product_id          AS product_id
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
            ,       0                       AS amount_to_invoice_intervention
            ,       0                       AS amount_to_invoice_service
            ,       0                       AS residual
        """
        return sub_select_account_invoice_line_str

    def _sub_from_account_invoice_line(self):
        sub_from_account_invoice_line_str = """
            FROM    account_invoice         AI
            ,       account_invoice_line    AIL
        """
        return sub_from_account_invoice_line_str

    def _sub_where_account_invoice_line(self):
        sub_where_account_invoice_line_str = """
            WHERE   AI.state            IN ('open', 'paid')
            AND     AI.type             IN ('out_invoice', 'out_refund')
            AND     AI.id               = AIL.invoice_id
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
            ,       OSOL.invoiced_turnover                      AS invoiced_turnover_budget
            ,       0                                           AS invoiced_total
            ,       0                                           AS previous_invoiced_total
            ,       0                                           AS margin_total
            ,       0                                           AS amount_to_invoice
            ,       0                                           AS amount_to_invoice_intervention
            ,       0                                           AS amount_to_invoice_service
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
            SELECT  30000000 + AIL.id   AS id
            ,       DATE(
                        EXTRACT(YEAR FROM AI.date_invoice) + 1 || '-' ||
                        TO_CHAR(AI.date_invoice, 'MM') || '-01'
                    )                   AS date
            ,       AI.company_id       AS company_id
            ,       AI.user_id          AS vendor_id
            ,       AI.partner_id       AS partner_id
            ,       AIL.product_id      AS product_id
            ,       0                   AS invoiced_turnover_budget
            ,       0                   AS invoiced_total
            ,       CASE
                        WHEN AI.type = 'out_invoice' THEN
                            AIL.price_subtotal
                        ELSE
                            -AIL.price_subtotal
                    END                 AS previous_invoiced_total
            ,       0                   AS margin_total
            ,       0                   AS amount_to_invoice
            ,       0                   AS amount_to_invoice_intervention
            ,       0                   AS amount_to_invoice_service
            ,       0                   AS residual
        """
        return sub_select_account_invoice_n_1_str

    def _sub_from_account_invoice_n_1(self):
        sub_from_account_invoice_n_1_str = """
            FROM    account_invoice         AI
            ,       account_invoice_line    AIL
        """
        return sub_from_account_invoice_n_1_str

    def _sub_where_account_invoice_n_1(self):
        sub_where_account_invoice_n_1_str = """
            WHERE   AI.state            IN ('open', 'paid')
            AND     AI.type             IN ('out_invoice', 'out_refund')
            AND     AIL.invoice_id      = AI.id
        """
        return sub_where_account_invoice_n_1_str

    def _sub_select_sale_order_line(self):
        sub_select_sale_order_line_str = """
            SELECT  40000000 + SOL.id                                               AS id
            ,       CASE
                        WHEN SOL.state = 'presale' THEN
                            SO.of_date_de_pose
                        WHEN SOL.product_id = %s THEN
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
            ,       SOL.product_id                                                  AS product_id
            ,       0                                                               AS invoiced_turnover_budget
            ,       0                                                               AS invoiced_total
            ,       0                                                               AS previous_invoiced_total
            ,       0                                                               AS margin_total
            ,       SOL.of_amount_to_invoice                                        AS amount_to_invoice
            ,       0                                                               AS amount_to_invoice_intervention
            ,       0                                                               AS amount_to_invoice_service
            ,       0                                                               AS residual
        """
        return sub_select_sale_order_line_str

    def _sub_from_sale_order_line(self):
        sub_from_sale_order_line_str = """
            FROM    sale_order          SO
            ,       sale_order_line     SOL
        """
        return sub_from_sale_order_line_str

    def _sub_where_sale_order_line(self):
        sub_where_sale_order_line_str = """
            WHERE   SOL.invoice_status          IN ('no', 'to invoice')
            AND     SOL.of_amount_to_invoice    != 0
            AND     SO.id                       = SOL.order_id
            AND     SO.state                    NOT IN ('draft', 'sent', 'closed', 'cancel')
        """
        return sub_where_sale_order_line_str

    def _sub_select_intervention(self):
        sub_select_intervention_str = """
            SELECT  50000000 + OPIL.id                          AS id
            ,       OPI.date                                    AS date
            ,       OPI.company_id                              AS company_id
            ,       OPI.user_id                                 AS vendor_id
            ,       OPI.partner_id                              AS partner_id
            ,       OPIL.product_id                             AS product_id
            ,       0                                           AS invoiced_turnover_budget
            ,       0                                           AS invoiced_total
            ,       0                                           AS previous_invoiced_total
            ,       0                                           AS margin_total
            ,       0                                           AS amount_to_invoice
            ,       OPIL.price_subtotal                         AS amount_to_invoice_intervention
            ,       0                                           AS amount_to_invoice_service
            ,       0                                           AS residual
        """
        return sub_select_intervention_str

    def _sub_from_intervention(self):
        sub_from_intervention_str = """
            FROM    of_planning_intervention        OPI
            ,       of_planning_intervention_line   OPIL
        """
        return sub_from_intervention_str

    def _sub_where_intervention(self):
        sub_where_intervention_str = """
            WHERE   OPIL.invoice_status         = 'to invoice'
            AND     OPIL.price_subtotal         != 0
            AND     OPI.id                      = OPIL.intervention_id
            AND     OPI.type_id                 = %s
        """ % self.env.ref('of_service.of_service_type_maintenance').id
        return sub_where_intervention_str

    def _sub_select_service(self):
        sub_select_service_str = """
            SELECT  60000000 + OSL.id                           AS id
            ,       OS.date_next                                AS date
            ,       OS.company_id                               AS company_id
            ,       OS.user_id                                  AS vendor_id
            ,       OS.partner_id                               AS partner_id
            ,       OSL.product_id                              AS product_id
            ,       0                                           AS invoiced_turnover_budget
            ,       0                                           AS invoiced_total
            ,       0                                           AS previous_invoiced_total
            ,       0                                           AS margin_total
            ,       0                                           AS amount_to_invoice
            ,       0                                           AS amount_to_invoice_intervention
            ,       OSL.price_subtotal                          AS amount_to_invoice_service
            ,       0                                           AS residual
        """
        return sub_select_service_str

    def _sub_from_service(self):
        sub_from_service_str = """
            FROM    of_service          OS
            ,       of_service_line     OSL
        """
        return sub_from_service_str

    def _sub_where_service(self):
        sub_where_service_str = """
            WHERE   OSL.price_subtotal          != 0
            AND     OSL.saleorder_line_id       IS NULL
            AND     OS.id                       = OSL.service_id
            AND     OS.base_state               = 'calculated'
            AND     OS.type_id                  = %s
        """ % self.env.ref('of_service.of_service_type_maintenance').id
        return sub_where_service_str

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
            ,           PT.categ_id
            ,           PT.brand_id
        """
        return group_by_str

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        fields_copy = fields
        if 'invoiced_total' not in fields_copy:
            fields_copy.append('invoiced_total')
        if 'invoiced_turnover_budget' not in fields_copy:
            fields_copy.append('invoiced_turnover_budget')
        if 'previous_invoiced_total' not in fields_copy:
            fields_copy.append('previous_invoiced_total')
        if 'amount_to_invoice' not in fields_copy:
            fields_copy.append('amount_to_invoice')
        if 'margin_total' not in fields_copy:
            fields_copy.append('margin_total')
        if 'amount_to_invoice_intervention' not in fields_copy:
            fields_copy.append('amount_to_invoice_intervention')

        res = super(OfInvoicedRevenueAnalysis, self).read_group(
            domain, fields_copy, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        for line in res:
            if 'margin_perc' in fields_copy:
                if 'margin_total' in line and line['margin_total'] is not None and line.get('invoiced_total', False):
                    line['margin_perc'] = \
                        ('%.2f' % (round(100.0 * line['margin_total'] / line['invoiced_total'], 2))).\
                        replace('.', ',')
                else:
                    line['margin_perc'] = "N/E"
            if 'landing_forecast_sales' in fields_copy:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        'amount_to_invoice' in line and line['amount_to_invoice'] is not None and \
                        'amount_to_invoice_intervention' in line and line['amount_to_invoice_intervention'] is not None:
                    value = line['invoiced_total'] + line['amount_to_invoice'] + line['amount_to_invoice_intervention']
                    line['landing_forecast_sales'] = '{:,.0f}'.format(value).replace(',', ' ').replace('.', ',')
                else:
                    line['landing_forecast_sales'] = "N/E"
            if 'invoiced_turnover_budget_gap' in fields_copy:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        'amount_to_invoice' in line and line['amount_to_invoice'] is not None and \
                        'amount_to_invoice_intervention' in line and \
                        line['amount_to_invoice_intervention'] is not None and \
                        'invoiced_turnover_budget' in line and line['invoiced_turnover_budget'] is not None:
                    value = (line['invoiced_total'] + line['amount_to_invoice'] +
                             line['amount_to_invoice_intervention']) - line['invoiced_turnover_budget']
                    line['invoiced_turnover_budget_gap'] = '{:,.0f}'.format(value).replace(',', ' ').replace('.', ',')
                else:
                    line['invoiced_turnover_budget_gap'] = "N/E"
            if 'invoiced_total_comparison' in fields_copy:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        line.get('previous_invoiced_total', False):
                    line['invoiced_total_comparison'] = \
                        ('%.2f' % (round(100.0 * line['invoiced_total'] / line['previous_invoiced_total'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_total_comparison'] = "N/E"
            if 'invoiced_turnover_budget_comparison' in fields_copy:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        line.get('invoiced_turnover_budget', False):
                    line['invoiced_turnover_budget_comparison'] = \
                        ('%.2f' % (round(100.0 * line['invoiced_total'] / line['invoiced_turnover_budget'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_turnover_budget_comparison'] = "N/E"

        return res
