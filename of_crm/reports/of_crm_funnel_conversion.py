# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools


class OFCRMFunnelConversion(models.Model):
    """Tunnel de conversion CRM 1"""

    _name = "of.crm.funnel.conversion"
    _auto = False
    _description = "Tunnel de conversion CRM 1"
    _rec_name = 'id'

    date = fields.Date(string=u"Date", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    vendor_id = fields.Many2one(comodel_name='res.users', string=u"Vendeur", readonly=True)
    project_id = fields.Many2one(comodel_name='account.analytic.account',string=u"Compte analytique", readonly=True)
    opportunity_nb = fields.Integer(string=u"Nombre d'opportunités", readonly=True)
    quotation_nb = fields.Integer(string=u"Nombre de devis", readonly=True)
    order_nb = fields.Integer(string=u"Nombre de commandes", readonly=True)
    quotation_rate = fields.Float(string=u"Taux de devis (%)", readonly=True, group_operator="avg")
    order_rate1 = fields.Float(string=u"Taux de concrétisation (%)", readonly=True, group_operator="avg")
    order_rate2 = fields.Float(string=u"Taux de transformation (%)", readonly=True, group_operator="avg")
    opportunity_cart = fields.Float(string=u"Panier opportunité", readonly=True, group_operator="avg")
    quotation_cart = fields.Float(string=u"Panier devis", readonly=True, group_operator="avg")
    order_cart = fields.Float(string=u"Panier moyen", readonly=True, group_operator="avg")
    activity_nb = fields.Integer(string=u"Nombre d'activités", readonly=True)
    quotation_amount = fields.Float(string=u"Montant devis", readonly=True)
    order_margin_percent = fields.Float(string=u"Marge % commandé", readonly=True, group_operator="avg")
    order_margin = fields.Float(string=u"Marge € commandé", readonly=True)
    sales_total = fields.Float(string=u"CA commandé", readonly=True)
    ordered_turnover_objective = fields.Float(string=u"Objectif CA commandé", readonly=True)
    sales_objective_comparison = fields.Char(
        string=u"Comparaison Objectif (%)", compute='_compute_sales_objective_comparison', compute_sudo=True,
        readonly=True)
    previous_sales_total = fields.Float(string=u"CA commandé N-1", readonly=True)
    order_amount_rate = fields.Char(
        string=u"Taux de concrétisation € (%)", compute='_compute_order_amount_rate', compute_sudo=True, readonly=True)
    sales_total_comparison = fields.Char(
        string=u"Comparaison N-1 (%)", compute='_compute_sales_total_comparison', compute_sudo=True, readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_crm_funnel_conversion')
        self._cr.execute("""
            CREATE VIEW of_crm_funnel_conversion AS (
                    SELECT      CL.id
                    ,           CL.of_date_prospection                                                                  AS date
                    ,           CL.company_id
                    ,           CL.user_id                                                                              AS vendor_id
                    ,           COALESCE(SO1.project_id, SO2.project_id)                                                AS project_id
                    ,           COUNT(DISTINCT CL.id)                                                                   AS opportunity_nb
                    ,           COUNT(DISTINCT SO1.opportunity_id)                                                      AS quotation_nb
                    ,           COUNT(DISTINCT SO2.opportunity_id)                                                      AS order_nb
                    ,           100 * COUNT(DISTINCT SO1.opportunity_id) / COUNT(DISTINCT CL.id)                        AS quotation_rate
                    ,           CASE
                                    WHEN COUNT(DISTINCT SO1.opportunity_id) = 0 THEN
                                        NULL
                                    ELSE
                                        100 * COUNT(DISTINCT SO2.opportunity_id) / COUNT(DISTINCT SO1.opportunity_id)
                                END                                                                                     AS order_rate1
                    ,           100 * COUNT(DISTINCT SO2.opportunity_id) / COUNT(DISTINCT CL.id)                        AS order_rate2
                    ,           COALESCE(SO2.amount_untaxed, 0)                                                         AS opportunity_cart
                    ,           CASE
                                    WHEN COUNT(DISTINCT SO1.opportunity_id) = 0 THEN
                                        NULL
                                    ELSE
                                        COALESCE(SO2.amount_untaxed, 0)
                                END                                                                                     AS quotation_cart
                    ,           CASE
                                    WHEN COUNT(DISTINCT SO2.opportunity_id) = 0 THEN
                                        NULL
                                    ELSE
                                        COALESCE(SO2.amount_untaxed, 0)
                                END                                                                                     AS order_cart
                    ,           COUNT(DISTINCT CA.id)                                                                   AS activity_nb
                    ,           CASE
                                    WHEN COUNT(DISTINCT SO3.opportunity_id) = 0 THEN
                                        0
                                    ELSE
                                        COALESCE(AVG(SO3.amount_untaxed), 0)
                                END                                                                                     AS quotation_amount
                    ,           CASE
                                    WHEN COUNT(DISTINCT SO2.opportunity_id) = 0 THEN
                                        NULL
                                    WHEN SO2.amount_untaxed = 0 THEN
                                        NULL
                                    ELSE
                                        100 * (1 - (SO2.amount_untaxed - SO2.margin) / SO2.amount_untaxed)
                                END                                                                                     AS order_margin_percent
                    ,           CASE
                                    WHEN COUNT(DISTINCT SO2.opportunity_id) = 0 THEN
                                        0
                                    ELSE
                                        COALESCE(SO2.margin, 0)
                                END                                                                                     AS order_margin
                    ,           COALESCE(SO2.amount_untaxed, 0)                                                         AS sales_total
                    ,           0                                                                                       AS ordered_turnover_objective
                    ,           0                                                                                       AS previous_sales_total
                    FROM        crm_lead                                                                                CL
                    LEFT JOIN   sale_order                                                                              SO1
                        ON      CL.id                                                                                   = SO1.opportunity_id
                    LEFT JOIN   sale_order                                                                              SO2
                        ON      CL.id                                                                                   = SO2.opportunity_id
                        AND     SO2.state                                                                               = 'sale'
                    LEFT JOIN   sale_order                                                                              SO3
                        ON      SO1.id                                                                                  = SO3.id
                        AND     SO3.state                                                                               != 'cancel'
                    LEFT JOIN   of_crm_activity                                                                         CA
                        ON      CA.opportunity_id                                                                       = CL.id
                        AND     CA.state                                                                                ='done'
                    GROUP BY    CL.id
                    ,           SO2.amount_untaxed
                    ,           SO2.margin
                    ,           SO1.project_id
                    ,           SO2.project_id
                UNION ALL
                    SELECT      1000000 + OSOL.id                                                                       AS id
                    ,           DATE(OSO.year || '-' || OSO.month || '-01')                                             AS date
                    ,           OSO.company_id                                                                          AS company_id
                    ,           RR.user_id                                                                              AS vendor_id
                    ,           NULL                                                                                    AS project_id
                    ,           0                                                                                       AS opportunity_nb
                    ,           0                                                                                       AS quotation_nb
                    ,           0                                                                                       AS order_nb
                    ,           NULL                                                                                    AS quotation_rate
                    ,           NULL                                                                                    AS order_rate1
                    ,           NULL                                                                                    AS order_rate2
                    ,           NULL                                                                                    AS opportunity_cart
                    ,           NULL                                                                                    AS quotation_cart
                    ,           NULL                                                                                    AS order_cart
                    ,           0                                                                                       AS activity_nb
                    ,           0                                                                                       AS quotation_amount
                    ,           NULL                                                                                    AS order_margin_percent
                    ,           0                                                                                       AS order_margin
                    ,           0                                                                                       AS sales_total
                    ,           OSOL.ordered_turnover                                                                   AS ordered_turnover_objective
                    ,           (   SELECT  SUM(SO.amount_untaxed)
                                    FROM    sale_order                                      SO
                                    ,       crm_lead                                        CL2
                                    WHERE   SO.user_id                                      = RR.user_id
                                    AND     EXTRACT(MONTH FROM CL2.of_date_prospection)     = TO_NUMBER(OSO.month, '99')
                                    AND     EXTRACT(YEAR FROM CL2.of_date_prospection)      = OSO.year - 1
                                    AND     SO.opportunity_id                               = CL2.id
                                    AND     SO.state                                        = 'sale'
                                )                                                                                       AS previous_sales_total
                    FROM        of_sale_objective                                                                       OSO
                    ,           of_sale_objective_line                                                                  OSOL
                    ,           hr_employee                                                                             HR
                    ,           resource_resource                                                                       RR
                    WHERE       OSOL.objective_id                                                                       = OSO.id
                    AND         HR.id                                                                                   = OSOL.employee_id
                    AND         RR.id                                                                                   = HR.resource_id
            )""")

    @api.multi
    def _compute_sales_objective_comparison(self):
        for rec in self:
            if rec.ordered_turnover_objective > 0:
                rec.sales_objective_comparison = '%.2f' % (100.0 * rec.sales_total / rec.ordered_turnover_objective)
            else:
                rec.sales_objective_comparison = "N/E"

    @api.multi
    def _compute_sales_total_comparison(self):
        for rec in self:
            if rec.previous_sales_total > 0:
                rec.sales_total_comparison = '%.2f' % (100.0 * rec.sales_total / rec.previous_sales_total)
            else:
                rec.sales_total_comparison = "N/E"

    @api.multi
    def _compute_order_amount_rate(self):
        for rec in self:
            if rec.quotation_amount > 0:
                rec.order_amount_rate = '%.2f' % (100.0 * rec.sales_total / rec.quotation_amount)
            else:
                rec.order_amount_rate = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(OFCRMFunnelConversion, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'sales_objective_comparison' in fields:
                if line['ordered_turnover_objective'] > 0:
                    line['sales_objective_comparison'] = \
                        ('%.2f' % (round(100.0 * line['sales_total'] / line['ordered_turnover_objective'], 2))).\
                        replace('.', ',')
                else:
                    line['sales_objective_comparison'] = "N/E"
            if 'sales_total_comparison' in fields:
                if line['previous_sales_total'] > 0:
                    line['sales_total_comparison'] = \
                        ('%.2f' % (round(100.0 * line['sales_total'] / line['previous_sales_total'], 2))).\
                        replace('.', ',')
                else:
                    line['sales_total_comparison'] = "N/E"
            if 'order_amount_rate' in fields:
                if line['quotation_amount'] > 0:
                    line['order_amount_rate'] = \
                        ('%.2f' % (round(100.0 * line['sales_total'] / line['quotation_amount'], 2))).replace('.', ',')
                else:
                    line['order_amount_rate'] = "N/E"

        return res


class OFCRMFunnelConversion2(models.Model):
    """Tunnel de conversion CRM 2"""

    _name = "of.crm.funnel.conversion2"
    _auto = False
    _description = "Tunnel de conversion CRM 2"
    _rec_name = 'id'

    date = fields.Date(string=u"Date", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    vendor_id = fields.Many2one(comodel_name='res.users', string=u"Vendeur", readonly=True)
    project_id = fields.Many2one(comodel_name='account.analytic.account',string=u"Compte analytique", readonly=True)
    opportunity_nb = fields.Integer(string=u"Nombre d'opportunités", readonly=True)
    quotation_nb = fields.Integer(string=u"Nombre de devis", readonly=True)
    order_nb = fields.Integer(string=u"Nombre de commandes", readonly=True)
    quotation_rate = fields.Char(
        string=u"Taux de devis (%)", compute='_compute_quotation_rate', compute_sudo=True, readonly=True)
    order_rate1 = fields.Char(
        string=u"Taux de concrétisation (%)", compute='_compute_order_rate1', compute_sudo=True, readonly=True)
    order_rate2 = fields.Char(
        string=u"Taux de transformation (%)", compute='_compute_order_rate2', compute_sudo=True, readonly=True)
    opportunity_cart = fields.Char(
        string=u"Panier opportunité", compute='_compute_opportunity_cart', compute_sudo=True, readonly=True)
    quotation_cart = fields.Char(
        string=u"Panier devis", compute='_compute_quotation_cart', compute_sudo=True, readonly=True)
    order_cart = fields.Char(
        string=u"Panier moyen", compute='_compute_order_cart', compute_sudo=True, readonly=True)
    activity_nb = fields.Integer(string=u"Nombre d'activités", readonly=True)
    quotation_amount = fields.Float(string=u"Montant devis", readonly=True)
    order_margin_percent = fields.Char(
        string=u"Marge % commandé", compute='_compute_order_margin_percent', compute_sudo=True, readonly=True)
    order_margin = fields.Float(string=u"Marge € commandé", readonly=True)
    sales_total = fields.Float(string=u"CA commandé", readonly=True)
    order_amount_rate = fields.Char(
        string=u"Taux de concrétisation € (%)", compute='_compute_order_amount_rate', compute_sudo=True, readonly=True)
    ordered_turnover_objective = fields.Float(string=u"Objectif CA commandé", readonly=True)
    sales_objective_comparison = fields.Char(
        string=u"Comparaison Objectif (%)", compute='_compute_sales_objective_comparison', compute_sudo=True,
        readonly=True)
    previous_sales_total = fields.Float(string=u"CA commandé N-1", readonly=True)
    sales_total_comparison = fields.Char(
        string=u"Comparaison N-1 (%)", compute='_compute_sales_total_comparison', compute_sudo=True, readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_crm_funnel_conversion2')
        self._cr.execute("""
            CREATE VIEW of_crm_funnel_conversion2 AS (
                SELECT      MAX(T.id)                                       AS id
                ,           T.date
                ,           T.company_id
                ,           T.vendor_id
                ,           T.project_id
                ,           COALESCE(SUM(T.opportunity_nb), 0)              AS opportunity_nb
                ,           COALESCE(SUM(T.quotation_nb), 0)                AS quotation_nb
                ,           COALESCE(SUM(T.order_nb), 0)                    AS order_nb
                ,           SUM(T.cart)                                     AS sales_total
                ,           SUM(T.activity_nb)                              AS activity_nb
                ,           SUM(T.quotation_amount)                         AS quotation_amount
                ,           SUM(T.order_margin)                             AS order_margin
                ,           SUM(T.ordered_turnover_objective)               AS ordered_turnover_objective
                ,           SUM(T.previous_sales_total)                     AS previous_sales_total
                FROM
                        (   SELECT      CL.id                               AS id
                            ,           CL.of_date_prospection              AS date
                            ,           CL.company_id                       AS company_id
                            ,           CL.user_id                          AS vendor_id
                            ,           NULL                                AS project_id
                            ,           1                                   AS opportunity_nb
                            ,           0                                   AS quotation_nb
                            ,           0                                   AS order_nb
                            ,           0                                   AS cart
                            ,           0                                   AS activity_nb
                            ,           0                                   AS quotation_amount
                            ,           0                                   AS order_margin
                            ,           0                                   AS ordered_turnover_objective
                            ,           0                                   AS previous_sales_total
                            FROM        crm_lead                            CL
                            GROUP BY    CL.id
                        UNION ALL
                            SELECT      1000000 + MAX(SO.id)                AS id
                            ,           DATE(MAX(SO.date_order))            AS date
                            ,           CL2.company_id                      AS company_id
                            ,           CL2.user_id                         AS vendor_id
                            ,           MAX(SO.project_id)                  AS project_id
                            ,           0                                   AS opportunity_nb
                            ,           1                                   AS quotation_nb
                            ,           0                                   AS order_nb
                            ,           0                                   AS cart
                            ,           0                                   AS activity_nb
                            ,           AVG(SO1.amount_untaxed)             AS quotation_amount
                            ,           0                                   AS order_margin
                            ,           0                                   AS ordered_turnover_objective
                            ,           0                                   AS previous_sales_total
                            FROM        sale_order                          SO
                            LEFT JOIN   sale_order                          SO1
                                ON      SO.id                               = SO1.id
                                AND     SO1.state                           != 'cancel'
                            ,           crm_lead                            CL2
                            WHERE       SO.opportunity_id                   IS NOT NULL
                            AND         CL2.id                              = SO.opportunity_id
                            GROUP BY    SO.opportunity_id
                            ,           CL2.company_id
                            ,           CL2.user_id
                        UNION ALL
                            SELECT      2000000 + MAX(SO2.id)               AS id
                            ,           DATE(MAX(SO2.confirmation_date))    AS date
                            ,           CL3.company_id                      AS company_id
                            ,           CL3.user_id                         AS vendor_id
                            ,           MAX(SO2.project_id)                 AS project_id
                            ,           0                                   AS opportunity_nb
                            ,           0                                   AS quotation_nb
                            ,           1                                   AS order_nb
                            ,           AVG(SO2.amount_untaxed)             AS cart
                            ,           0                                   AS activity_nb
                            ,           0                                   AS quotation_amount
                            ,           AVG(SO2.margin)                     AS order_margin
                            ,           0                                   AS ordered_turnover_objective
                            ,           0                                   AS previous_sales_total
                            FROM        sale_order                          SO2
                            ,           crm_lead                            CL3
                            WHERE       SO2.opportunity_id                  IS NOT NULL
                            AND         SO2.state                           = 'sale'
                            AND         CL3.id                              = SO2.opportunity_id
                            GROUP BY    SO2.opportunity_id
                            ,           CL3.company_id
                            ,           CL3.user_id
                        UNION ALL
                            SELECT      3000000 + CA.id                     AS id
                            ,           DATE(CA.date)                       AS date
                            ,           CL4.company_id                      AS company_id
                            ,           CA.vendor_id                        AS vendor_id
                            ,           NULL                                AS project_id
                            ,           0                                   AS opportunity_nb
                            ,           0                                   AS quotation_nb
                            ,           0                                   AS order_nb
                            ,           0                                   AS cart
                            ,           1                                   AS activity_nb
                            ,           0                                   AS quotation_amount
                            ,           0                                   AS order_margin
                            ,           0                                   AS ordered_turnover_objective
                            ,           0                                   AS previous_sales_total
                            FROM        of_crm_activity                     CA
                            ,           crm_lead                            CL4
                            WHERE       CA.opportunity_id                   = CL4.id
                            AND         CA.state                            ='done'
                        UNION ALL
                            SELECT      4000000 + OSOL.id                           AS id
                            ,           DATE(OSO.year || '-' || OSO.month || '-01') AS date
                            ,           OSO.company_id                              AS company_id
                            ,           RR.user_id                                  AS vendor_id
                            ,           NULL                                        AS project_id
                            ,           0                                           AS opportunity_nb
                            ,           0                                           AS quotation_nb
                            ,           0                                           AS order_nb
                            ,           0                                           AS cart
                            ,           0                                           AS activity_nb
                            ,           0                                           AS quotation_amount
                            ,           0                                           AS order_margin
                            ,           OSOL.ordered_turnover                       AS ordered_turnover_objective
                            ,           (   SELECT  SUM(SO3.amount_untaxed)
                                            FROM    sale_order                                  SO3
                                            WHERE   SO3.user_id                                 = RR.user_id
                                            AND     EXTRACT(MONTH FROM SO3.confirmation_date)   = TO_NUMBER(OSO.month, '99')
                                            AND     EXTRACT(YEAR FROM SO3.confirmation_date)    = OSO.year - 1
                                            AND     SO3.state                                   = 'sale'
                                        )                                           AS previous_sales_total
                            FROM        of_sale_objective                           OSO
                            ,           of_sale_objective_line                      OSOL
                            ,           hr_employee                                 HR
                            ,           resource_resource                           RR
                            WHERE       OSOL.objective_id                           = OSO.id
                            AND         HR.id                                       = OSOL.employee_id
                            AND         RR.id                                       = HR.resource_id
                        )                                                           AS T
                GROUP BY    T.date
                ,           T.company_id
                ,           T.vendor_id
                ,           T.project_id
            )""")

    @api.multi
    def _compute_quotation_rate(self):
        for rec in self:
            if rec.opportunity_nb > 0:
                rec.quotation_rate = '%.2f' % (100.0 * rec.quotation_nb / rec.opportunity_nb)
            else:
                rec.quotation_rate = "N/E"

    @api.multi
    def _compute_order_rate1(self):
        for rec in self:
            if rec.quotation_nb > 0:
                rec.order_rate1 = '%.2f' % (100.0 * rec.order_nb / rec.quotation_nb)
            else:
                rec.order_rate1 = "N/E"

    @api.multi
    def _compute_order_rate2(self):
        for rec in self:
            if rec.opportunity_nb > 0:
                rec.order_rate2 = '%.2f' % (100.0 * rec.order_nb / rec.opportunity_nb)
            else:
                rec.order_rate2 = "N/E"

    @api.multi
    def _compute_opportunity_cart(self):
        for rec in self:
            if rec.opportunity_nb > 0:
                rec.opportunity_cart = '%.2f' % (rec.sales_total / rec.opportunity_nb)
            else:
                rec.opportunity_cart = "N/E"

    @api.multi
    def _compute_quotation_cart(self):
        for rec in self:
            if rec.quotation_nb > 0:
                rec.quotation_cart = '%.2f' % (rec.sales_total / rec.quotation_nb)
            else:
                rec.quotation_cart = "N/E"

    @api.multi
    def _compute_order_cart(self):
        for rec in self:
            if rec.order_nb > 0:
                rec.order_cart = '%.2f' % (rec.sales_total / rec.order_nb)
            else:
                rec.order_cart = "N/E"

    @api.multi
    def _compute_order_margin_percent(self):
        for rec in self:
            if rec.sales_total > 0:
                rec.order_margin_percent = '%.2f' % \
                                           (100 * (1 - (rec.sales_total - rec.order_margin) / rec.sales_total))
            else:
                rec.order_margin_percent = "N/E"

    @api.multi
    def _compute_order_amount_rate(self):
        for rec in self:
            if rec.quotation_amount > 0:
                rec.order_amount_rate = '%.2f' % (100.0 * rec.sales_total / rec.quotation_amount)
            else:
                rec.order_amount_rate = "N/E"

    @api.multi
    def _compute_sales_objective_comparison(self):
        for rec in self:
            if rec.ordered_turnover_objective > 0:
                rec.sales_objective_comparison = '%.2f' % (100.0 * rec.sales_total / rec.ordered_turnover_objective)
            else:
                rec.sales_objective_comparison = "N/E"

    @api.multi
    def _compute_sales_total_comparison(self):
        for rec in self:
            if rec.previous_sales_total > 0:
                rec.sales_total_comparison = '%.2f' % (100.0 * rec.sales_total / rec.previous_sales_total)
            else:
                rec.sales_total_comparison = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(OFCRMFunnelConversion2, self).read_group(
            domain, fields.extend(['sales_total']), groupby, offset=offset, limit=limit,
            orderby=orderby, lazy=lazy)
        for line in res:
            if 'quotation_rate' in fields:
                if line['opportunity_nb'] > 0:
                    line['quotation_rate'] = \
                        ('%.2f' % (round(100.0 * line['quotation_nb'] / line['opportunity_nb'], 2))).replace('.', ',')
                else:
                    line['quotation_rate'] = "N/E"
            if 'order_rate1' in fields:
                if line['quotation_nb'] > 0:
                    line['order_rate1'] = ('%.2f' % (round(100.0 * line['order_nb'] / line['quotation_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['order_rate1'] = "N/E"
            if 'order_rate2' in fields:
                if line['opportunity_nb'] > 0:
                    line['order_rate2'] = ('%.2f' % (round(100.0 * line['order_nb'] / line['opportunity_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['order_rate2'] = "N/E"
            if 'opportunity_cart' in fields:
                if line['opportunity_nb'] > 0:
                    line['opportunity_cart'] = ('%.2f' % (round(line['sales_total'] / line['opportunity_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['opportunity_cart'] = "N/E"
            if 'quotation_cart' in fields:
                if line['quotation_nb'] > 0:
                    line['quotation_cart'] = ('%.2f' % (round(line['sales_total'] / line['quotation_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['quotation_cart'] = "N/E"
            if 'order_cart' in fields:
                if line['order_nb'] > 0:
                    line['order_cart'] = ('%.2f' % (round(line['sales_total'] / line['order_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['order_cart'] = "N/E"
            if 'order_margin_percent' in fields:
                if line['sales_total'] > 0:
                    line['order_margin_percent'] = \
                        ('%.2f' %
                         (round(100 * (1 - (line['sales_total'] - line['order_margin']) / line['sales_total']),
                                2))).replace('.', ',')
                else:
                    line['order_margin_percent'] = "N/E"
            if 'order_amount_rate' in fields:
                if line['quotation_amount'] > 0:
                    line['order_amount_rate'] = \
                        ('%.2f' % (round(100.0 * line['sales_total'] / line['quotation_amount'], 2))).replace('.', ',')
                else:
                    line['order_amount_rate'] = "N/E"
            if 'sales_objective_comparison' in fields:
                if line['ordered_turnover_objective'] > 0:
                    line['sales_objective_comparison'] = \
                        ('%.2f' % (round(100.0 * line['sales_total'] / line['ordered_turnover_objective'], 2))).\
                        replace('.', ',')
                else:
                    line['sales_objective_comparison'] = "N/E"
            if 'sales_total_comparison' in fields:
                if line['previous_sales_total'] > 0:
                    line['sales_total_comparison'] = \
                        ('%.2f' % (round(100.0 * line['sales_total'] / line['previous_sales_total'], 2))).\
                        replace('.', ',')
                else:
                    line['sales_total_comparison'] = "N/E"

        return res
