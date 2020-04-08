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
                ,           COALESCE(SO2.amount_total, 0)                                                           AS opportunity_cart
                ,           CASE
                                WHEN COUNT(DISTINCT SO1.opportunity_id) = 0 THEN
                                    NULL
                                ELSE
                                    COALESCE(SO2.amount_total, 0)
                            END                                                                                     AS quotation_cart
                ,           CASE
                                WHEN COUNT(DISTINCT SO2.opportunity_id) = 0 THEN
                                    NULL
                                ELSE
                                    COALESCE(SO2.amount_total, 0)
                            END                                                                                     AS order_cart
                ,           COUNT(DISTINCT CA.id)                                                                   AS activity_nb
                FROM        crm_lead                                                                                CL
                LEFT JOIN   sale_order                                                                              SO1
                    ON      CL.id                                                                                   = SO1.opportunity_id
                LEFT JOIN   sale_order                                                                              SO2
                    ON      CL.id                                                                                   = SO2.opportunity_id
                    AND     SO2.state                                                                               = 'sale'
                LEFT JOIN   of_crm_activity                                                                         CA
                    ON      CA.opportunity_id                                                                       = CL.id
                    AND     CA.state                                                                                ='realized'
                GROUP BY    CL.id
                ,           SO2.amount_total
                ,           SO1.project_id
                ,           SO2.project_id
            )""")


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
    total_cart = fields.Float(string=u"Panier total", readonly=True)
    opportunity_cart = fields.Char(
        string=u"Panier opportunité", compute='_compute_opportunity_cart', compute_sudo=True, readonly=True)
    quotation_cart = fields.Char(
        string=u"Panier devis", compute='_compute_quotation_cart', compute_sudo=True, readonly=True)
    order_cart = fields.Char(
        string=u"Panier moyen", compute='_compute_order_cart', compute_sudo=True, readonly=True)
    activity_nb = fields.Integer(string=u"Nombre d'activités", readonly=True)

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
                ,           SUM(T.cart)                                     AS total_cart
                ,           SUM(T.activity_nb)                              AS activity_nb
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
                            FROM        sale_order                          SO
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
                            ,           AVG(SO2.amount_total)               AS cart
                            ,           0                                   AS activity_nb
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
                            FROM        of_crm_activity                     CA
                            ,           crm_lead                            CL4
                            WHERE       CA.opportunity_id                   = CL4.id
                            AND         CA.state                            ='realized'
                        )                                                   AS T
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
                rec.opportunity_cart = '%.2f' % (rec.total_cart / rec.opportunity_nb)
            else:
                rec.opportunity_cart = "N/E"

    @api.multi
    def _compute_quotation_cart(self):
        for rec in self:
            if rec.quotation_nb > 0:
                rec.quotation_cart = '%.2f' % (rec.total_cart / rec.quotation_nb)
            else:
                rec.quotation_cart = "N/E"

    @api.multi
    def _compute_order_cart(self):
        for rec in self:
            if rec.order_nb > 0:
                rec.order_cart = '%.2f' % (rec.total_cart / rec.order_nb)
            else:
                rec.order_cart = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(OFCRMFunnelConversion2, self).read_group(domain, fields.append('total_cart'), groupby,
                                                             offset=offset, limit=limit, orderby=orderby, lazy=lazy)
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
                    line['opportunity_cart'] = ('%.2f' % (round(line['total_cart'] / line['opportunity_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['opportunity_cart'] = "N/E"
            if 'quotation_cart' in fields:
                if line['quotation_nb'] > 0:
                    line['quotation_cart'] = ('%.2f' % (round(line['total_cart'] / line['quotation_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['quotation_cart'] = "N/E"
            if 'order_cart' in fields:
                if line['order_nb'] > 0:
                    line['order_cart'] = ('%.2f' % (round(line['total_cart'] / line['order_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['order_cart'] = "N/E"

        return res
