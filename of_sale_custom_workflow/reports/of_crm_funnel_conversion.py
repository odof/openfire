# -*- coding: utf-8 -*-

from ast import literal_eval
import base64
from cStringIO import StringIO
import xlsxwriter
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, tools
from odoo.tools.safe_eval import safe_eval


class OFCRMFunnelConversion4(models.Model):
    """Tunnel de conversion CRM 4"""

    _name = "of.crm.funnel.conversion4"
    _auto = False
    _description = "Tunnel de conversion CRM 4"
    _rec_name = 'id'

    date = fields.Date(string=u"Date", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    company_type_id = fields.Many2one(comodel_name='of.res.company.type', string=u"Type de société", readonly=True)
    company_sector_id = fields.Many2one(
        comodel_name='of.res.company.sector', string=u"Secteur de société", readonly=True)
    company_sales_group_id = fields.Many2one(
        comodel_name='of.res.company.sales.group', string=u"Groupe Ventes de société", readonly=True)
    vendor_id = fields.Many2one(comodel_name='res.users', string=u"Vendeur", readonly=True)
    project_id = fields.Many2one(comodel_name='account.analytic.account', string=u"Compte analytique", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire", readonly=True)

    opportunity_nb = fields.Integer(string=u"Nb opportunités", readonly=True)
    quotation_nb = fields.Integer(string=u"Nb devis", readonly=True)
    order_nb = fields.Integer(string=u"Nb ventes", readonly=True)
    lost_quotation_nb = fields.Integer(string=u"Nb devis perdus", readonly=True)

    quotation_amount = fields.Float(string=u"Montant devis", readonly=True)
    ordered_turnover = fields.Float(string=u"CA commandé", readonly=True)
    recorded_turnover = fields.Float(string=u"CA enregistré", readonly=True)
    lost_turnover = fields.Float(string=u"CA perdu", readonly=True)
    total_turnover = fields.Float(string=u"CA total", readonly=True)

    ordered_margin = fields.Float(string=u"Marge commandé €", readonly=True)
    recorded_margin = fields.Float(string=u"Marge enregistré €", readonly=True)
    total_margin = fields.Float(string=u"Marge total €", readonly=True)

    budget_turnover_objective = fields.Float(string=u"Budget", readonly=True)
    ordered_turnover_objective = fields.Float(string=u"Objectif CA", readonly=True)
    previous_recorded_turnover = fields.Float(string=u"CA enregistré N-1", readonly=True)

    quotation_rate = fields.Char(
        string=u"Nb devis / Nb opportunités (%)", compute='_compute_quotation_rate', compute_sudo=True, readonly=True)
    order_rate = fields.Char(
        string=u"Nb ventes / Nb devis (%)", compute='_compute_order_rate', compute_sudo=True, readonly=True)

    turnover_rate = fields.Char(
        string=u"CA total / Montant devis (%)", compute='_compute_turnover_rate', compute_sudo=True, readonly=True)

    quotation_cart = fields.Char(
        string=u"Panier devis", compute='_compute_quotation_cart', compute_sudo=True, readonly=True)
    sale_cart = fields.Char(
        string=u"Panier vente", compute='_compute_sale_cart', compute_sudo=True, readonly=True)
    lost_cart = fields.Char(
        string=u"Panier perdu", compute='_compute_lost_cart', compute_sudo=True, readonly=True)

    ordered_margin_percent = fields.Char(
        string=u"Marge commandé %", compute='_compute_ordered_margin_percent', compute_sudo=True, readonly=True)
    recorded_margin_percent = fields.Char(
        string=u"Marge enregistré %", compute='_compute_recorded_margin_percent', compute_sudo=True, readonly=True)
    total_margin_percent = fields.Char(
        string=u"Marge total %", compute='_compute_total_margin_percent', compute_sudo=True, readonly=True)

    rest_to_do = fields.Char(string=u"RAF (%)", compute='_compute_rest_to_do', compute_sudo=True, readonly=True)
    total_turnover_comparison = fields.Char(
        string=u"Comparaison N-1 (%)", compute='_compute_total_turnover_comparison', compute_sudo=True, readonly=True)

    def init(self):
        lost_opportunity_stage_id = self.env['ir.values'].get_default(
            'sale.config.settings', 'of_lost_opportunity_stage_id')
        tools.drop_view_if_exists(self._cr, 'of_crm_funnel_conversion4')
        self._cr.execute("""
            CREATE VIEW of_crm_funnel_conversion4 AS (
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
                    )           AS T
                %s
                %s
                %s
            )""" % (self._select(),
                    self._sub_select_lead(),
                    self._sub_from_lead(),
                    self._sub_where_lead(),
                    self._sub_select_quotation(),
                    self._sub_from_quotation(),
                    self._sub_where_quotation(),
                    self._sub_select_order(),
                    self._sub_from_order(),
                    self._sub_where_order(),
                    self._sub_select_presale_order(),
                    self._sub_from_presale_order(),
                    self._sub_where_presale_order(),
                    self._sub_select_sale_order(),
                    self._sub_from_sale_order(),
                    self._sub_where_sale_order(),
                    self._sub_select_lost_order(),
                    self._sub_from_lost_order(),
                    self._sub_where_lost_order(),
                    self._sub_select_objective(),
                    self._sub_from_objective(),
                    self._sub_where_objective(),
                    self._from(),
                    self._where(),
                    self._group_by()))

    def _select(self):
        select_str = """
            SELECT      MAX(T.id)                                       AS id
            ,           T.date::date                                    AS date
            ,           T.company_id
            ,           RC.of_company_type_id                           AS company_type_id
            ,           RC.of_company_sector_id                         AS company_sector_id
            ,           RC.of_company_sales_group_id                    AS company_sales_group_id
            ,           T.vendor_id
            ,           T.project_id
            ,           T.partner_id
            ,           COALESCE(SUM(T.opportunity_nb), 0)              AS opportunity_nb
            ,           COALESCE(SUM(T.quotation_nb), 0)                AS quotation_nb
            ,           COALESCE(SUM(T.order_nb), 0)                    AS order_nb
            ,           COALESCE(SUM(T.lost_quotation_nb), 0)           AS lost_quotation_nb
            ,           SUM(T.quotation_amount)                         AS quotation_amount
            ,           SUM(T.ordered_turnover)                         AS ordered_turnover
            ,           SUM(T.recorded_turnover)                        AS recorded_turnover
            ,           SUM(T.lost_turnover)                            AS lost_turnover
            ,           SUM(T.ordered_turnover + T.recorded_turnover)   AS total_turnover
            ,           SUM(T.ordered_margin)                           AS ordered_margin
            ,           SUM(T.recorded_margin)                          AS recorded_margin
            ,           SUM(T.ordered_margin + T.recorded_margin)       AS total_margin
            ,           SUM(T.budget_turnover_objective)                AS budget_turnover_objective
            ,           SUM(T.ordered_turnover_objective)               AS ordered_turnover_objective
            ,           SUM(T.previous_recorded_turnover)               AS previous_recorded_turnover
        """
        return select_str

    def _sub_select_lead(self):
        sub_select_lead_str = """
            SELECT  CL.id                   AS id
            ,       CL.of_date_prospection  AS date
            ,       CL.company_id           AS company_id
            ,       CL.user_id              AS vendor_id
            ,       NULL                    AS project_id
            ,       CL.partner_id           AS partner_id
            ,       1                       AS opportunity_nb
            ,       0                       AS quotation_nb
            ,       0                       AS order_nb
            ,       0                       AS lost_quotation_nb
            ,       0                       AS quotation_amount
            ,       0                       AS ordered_turnover
            ,       0                       AS recorded_turnover
            ,       0                       AS lost_turnover
            ,       0                       AS ordered_margin
            ,       0                       AS recorded_margin
            ,       0                       AS budget_turnover_objective
            ,       0                       AS ordered_turnover_objective
            ,       0                       AS previous_recorded_turnover
        """
        return sub_select_lead_str

    def _sub_from_lead(self):
        sub_from_lead_str = """
            FROM    crm_lead    CL
        """
        return sub_from_lead_str

    def _sub_where_lead(self):
        sub_where_lead_str = ""
        return sub_where_lead_str

    def _sub_select_quotation(self):
        sub_select_quotation_str = """
            SELECT  10000000 + SO.id                                AS id
            ,       SO.create_date                                  AS date
            ,       SO.company_id                                   AS company_id
            ,       SO.user_id                                      AS vendor_id
            ,       SO.project_id                                   AS project_id
            ,       SO.partner_id                                   AS partner_id
            ,       0                                               AS opportunity_nb
            ,       CASE
                        WHEN SO.of_cancelled_order_id IS NULL THEN
                            1
                        ELSE
                            -1
                    END                                             AS quotation_nb
            ,       0                                               AS order_nb
            ,       0                                               AS lost_quotation_nb
            ,       SO.amount_untaxed                               AS quotation_amount
            ,       0                                               AS ordered_turnover
            ,       0                                               AS recorded_turnover
            ,       0                                               AS lost_turnover
            ,       0                                               AS ordered_margin
            ,       0                                               AS recorded_margin
            ,       0                                               AS budget_turnover_objective
            ,       0                                               AS ordered_turnover_objective
            ,       0                                               AS previous_recorded_turnover
        """
        return sub_select_quotation_str

    def _sub_from_quotation(self):
        sub_from_quotation_str = """
            FROM    sale_order  SO
        """
        return sub_from_quotation_str

    def _sub_where_quotation(self):
        sub_where_quotation_str = ""
        return sub_where_quotation_str

    def _sub_select_order(self):
        sub_select_order_str = """
            SELECT  20000000 + SO2.id                               AS id
            ,       SO2.of_custom_confirmation_date                 AS date
            ,       SO2.company_id                                  AS company_id
            ,       SO2.user_id                                     AS vendor_id
            ,       SO2.project_id                                  AS project_id
            ,       SO2.partner_id                                  AS partner_id
            ,       0                                               AS opportunity_nb
            ,       0                                               AS quotation_nb
            ,       CASE
                        WHEN SO2.of_cancelled_order_id IS NULL THEN
                            1
                        ELSE
                            -1
                    END                                             AS order_nb
            ,       0                                               AS lost_quotation_nb
            ,       0                                               AS quotation_amount
            ,       0                                               AS ordered_turnover
            ,       0                                               AS recorded_turnover
            ,       0                                               AS lost_turnover
            ,       0                                               AS ordered_margin
            ,       0                                               AS recorded_margin
            ,       0                                               AS budget_turnover_objective
            ,       0                                               AS ordered_turnover_objective
            ,       0                                               AS previous_recorded_turnover
        """
        return sub_select_order_str

    def _sub_from_order(self):
        sub_from_order_str = """
            FROM    sale_order  SO2
        """
        return sub_from_order_str

    def _sub_where_order(self):
        sub_where_order_str = """
            WHERE   SO2.state   NOT IN ('draft', 'sent', 'cancel')
        """
        return sub_where_order_str

    def _sub_select_presale_order(self):
        sub_select_presale_order_str = """
            SELECT  30000000 + SO3.id               AS id
            ,       SO3.of_custom_confirmation_date AS date
            ,       SO3.company_id                  AS company_id
            ,       SO3.user_id                     AS vendor_id
            ,       SO3.project_id                  AS project_id
            ,       SO3.partner_id                  AS partner_id
            ,       0                               AS opportunity_nb
            ,       0                               AS quotation_nb
            ,       0                               AS order_nb
            ,       0                               AS lost_quotation_nb
            ,       0                               AS quotation_amount
            ,       SO3.amount_untaxed              AS ordered_turnover
            ,       0                               AS recorded_turnover
            ,       0                               AS lost_turnover
            ,       SO3.margin                      AS ordered_margin
            ,       0                               AS recorded_margin
            ,       0                               AS budget_turnover_objective
            ,       0                               AS ordered_turnover_objective
            ,       0                               AS previous_recorded_turnover
        """
        return sub_select_presale_order_str

    def _sub_from_presale_order(self):
        sub_from_presale_order_str = """
            FROM    sale_order  SO3
        """
        return sub_from_presale_order_str

    def _sub_where_presale_order(self):
        sub_where_presale_order_str = """
            WHERE   SO3.state   = 'presale'
        """
        return sub_where_presale_order_str

    def _sub_select_sale_order(self):
        sub_select_sale_order_str = """
            SELECT  40000000 + SO4.id       AS id
            ,       SO4.confirmation_date   AS date
            ,       SO4.company_id          AS company_id
            ,       SO4.user_id             AS vendor_id
            ,       SO4.project_id          AS project_id
            ,       SO4.partner_id          AS partner_id
            ,       0                       AS opportunity_nb
            ,       0                       AS quotation_nb
            ,       0                       AS order_nb
            ,       0                       AS lost_quotation_nb
            ,       0                       AS quotation_amount
            ,       0                       AS ordered_turnover
            ,       SO4.amount_untaxed      AS recorded_turnover
            ,       0                       AS lost_turnover
            ,       0                       AS ordered_margin
            ,       SO4.margin              AS recorded_margin
            ,       0                       AS budget_turnover_objective
            ,       0                       AS ordered_turnover_objective
            ,       0                       AS previous_recorded_turnover
        """
        return sub_select_sale_order_str

    def _sub_from_sale_order(self):
        sub_from_sale_order_str = """
            FROM    sale_order  SO4
        """
        return sub_from_sale_order_str

    def _sub_where_sale_order(self):
        sub_where_sale_order_str = """
            WHERE   SO4.state   NOT IN ('draft', 'sent', 'cancel', 'presale')
        """
        return sub_where_sale_order_str

    def _sub_select_lost_order(self):
        sub_select_lost_order_str = """
            SELECT  50000000 + SO5.id   AS id
            ,       SO5.create_date     AS date
            ,       SO5.company_id      AS company_id
            ,       SO5.user_id         AS vendor_id
            ,       SO5.project_id      AS project_id
            ,       SO5.partner_id      AS partner_id
            ,       0                   AS opportunity_nb
            ,       0                   AS quotation_nb
            ,       0                   AS order_nb
            ,       1                   AS lost_quotation_nb
            ,       0                   AS quotation_amount
            ,       0                   AS ordered_turnover
            ,       0                   AS recorded_turnover
            ,       SO5.amount_untaxed  AS lost_turnover
            ,       0                   AS ordered_margin
            ,       0                   AS recorded_margin
            ,       0                   AS budget_turnover_objective
            ,       0                   AS ordered_turnover_objective
            ,       0                   AS previous_recorded_turnover
        """
        return sub_select_lost_order_str

    def _sub_from_lost_order(self):
        sub_from_lost_order_str = """
            FROM    sale_order  SO5
            ,       crm_lead    CL2
            ,       ir_values   IV
        """
        return sub_from_lost_order_str

    def _sub_where_lost_order(self):
        sub_where_lost_order_str = """
            WHERE   SO5.state       = 'cancel'
            AND     CL2.id          = SO5.opportunity_id
            AND     IV.name         = 'of_lost_opportunity_stage_id'
            AND     CL2.stage_id    = SUBSTRING(IV.value FROM 2 FOR CHAR_LENGTH(IV.value) - 2)::integer
        """
        return sub_where_lost_order_str

    def _sub_select_objective(self):
        sub_select_objective_str = """
            SELECT  60000000 + OSOL.id                          AS id
            ,       DATE(OSO.year || '-' || OSO.month || '-01') AS date
            ,       OSO.company_id                              AS company_id
            ,       RR.user_id                                  AS vendor_id
            ,       NULL                                        AS project_id
            ,       NULL                                        AS partner_id
            ,       0                                           AS opportunity_nb
            ,       0                                           AS quotation_nb
            ,       0                                           AS order_nb
            ,       0                                           AS lost_quotation_nb
            ,       0                                           AS quotation_amount
            ,       0                                           AS ordered_turnover
            ,       0                                           AS recorded_turnover
            ,       0                                           AS lost_turnover
            ,       0                                           AS ordered_margin
            ,       0                                           AS recorded_margin
            ,       OSOL.turnover_budget                        AS budget_turnover_objective
            ,       OSOL.ordered_turnover                       AS ordered_turnover_objective
            ,       (   SELECT  SUM(SO6.amount_untaxed)
                        FROM    sale_order                                  SO6
                        WHERE   SO6.user_id                                 = RR.user_id
                        AND     EXTRACT(MONTH FROM SO6.confirmation_date)   = TO_NUMBER(OSO.month, '99')
                        AND     EXTRACT(YEAR FROM SO6.confirmation_date)    = OSO.year - 1
                        AND     SO6.state                                   NOT IN ('draft', 'sent', 'cancel', 'presale')
                    )                                           AS previous_recorded_turnover
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

    def _from(self):
        from_str = """
            ,   res_company AS RC
        """
        return from_str

    def _where(self):
        where_str = """
            WHERE   RC.id   = T.company_id
        """
        return where_str

    def _group_by(self):
        group_by_str = """
            GROUP BY    T.date
            ,           T.company_id
            ,           RC.of_company_type_id
            ,           RC.of_company_sector_id
            ,           RC.of_company_sales_group_id
            ,           T.vendor_id
            ,           T.project_id
            ,           T.partner_id
        """
        return group_by_str

    @api.multi
    def _compute_quotation_rate(self):
        for rec in self:
            if rec.opportunity_nb != 0:
                rec.quotation_rate = '%.2f' % (100.0 * rec.quotation_nb / rec.opportunity_nb)
            else:
                rec.quotation_rate = "N/E"

    @api.multi
    def _compute_order_rate(self):
        for rec in self:
            if rec.quotation_nb != 0:
                rec.order_rate = '%.2f' % (100.0 * rec.order_nb / rec.quotation_nb)
            else:
                rec.order_rate = "N/E"

    @api.multi
    def _compute_turnover_rate(self):
        for rec in self:
            if rec.quotation_amount != 0:
                rec.turnover_rate = '%.2f' % \
                    (100.0 * rec.total_turnover / rec.quotation_amount)
            else:
                rec.turnover_rate = "N/E"

    @api.multi
    def _compute_quotation_cart(self):
        for rec in self:
            if rec.quotation_nb != 0:
                rec.quotation_cart = '%.2f' % (rec.total_turnover / rec.quotation_nb)
            else:
                rec.quotation_cart = "N/E"

    @api.multi
    def _compute_sale_cart(self):
        for rec in self:
            if rec.order_nb != 0:
                rec.sale_cart = '%.2f' % (rec.total_turnover / rec.order_nb)
            else:
                rec.sale_cart = "N/E"

    @api.multi
    def _compute_lost_cart(self):
        for rec in self:
            if rec.lost_quotation_nb != 0:
                rec.lost_cart = '%.2f' % (rec.lost_turnover / rec.lost_quotation_nb)
            else:
                rec.lost_cart = "N/E"

    @api.multi
    def _compute_ordered_margin_percent(self):
        for rec in self:
            if rec.ordered_turnover != 0:
                rec.ordered_margin_percent = '%.2f' % \
                    (100 * (1 - (rec.ordered_turnover - rec.ordered_margin) / rec.ordered_turnover))
            else:
                rec.ordered_margin_percent = "N/E"

    @api.multi
    def _compute_recorded_margin_percent(self):
        for rec in self:
            if rec.recorded_turnover != 0:
                rec.recorded_margin_percent = '%.2f' % \
                    (100 * (1 - (rec.recorded_turnover - rec.recorded_margin) / rec.recorded_turnover))
            else:
                rec.recorded_margin_percent = "N/E"

    @api.multi
    def _compute_total_margin_percent(self):
        for rec in self:
            if rec.total_turnover != 0:
                rec.total_margin_percent = '%.2f' % \
                    (100 * (1 - (rec.total_turnover - rec.total_margin) / rec.total_turnover))
            else:
                rec.total_margin_percent = "N/E"

    @api.multi
    def _compute_rest_to_do(self):
        for rec in self:
            if rec.ordered_turnover_objective != 0:
                rec.rest_to_do = '%.2f' % (100.0 * rec.total_turnover / rec.ordered_turnover_objective)
            else:
                rec.rest_to_do = "N/E"

    @api.multi
    def _compute_total_turnover_comparison(self):
        for rec in self:
            if rec.previous_recorded_turnover != 0:
                rec.total_turnover_comparison = '%.2f' % (100.0 * rec.total_turnover / rec.previous_recorded_turnover)
            else:
                rec.total_turnover_comparison = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        fields_copy = fields
        if 'quotation_nb' not in fields_copy:
            fields_copy.append('quotation_nb')
        if 'opportunity_nb' not in fields_copy:
            fields_copy.append('opportunity_nb')
        if 'order_nb' not in fields_copy:
            fields_copy.append('order_nb')
        if 'total_turnover' not in fields_copy:
            fields_copy.append('total_turnover')
        if 'lost_turnover' not in fields_copy:
            fields_copy.append('lost_turnover')
        if 'lost_quotation_nb' not in fields_copy:
            fields_copy.append('lost_quotation_nb')
        if 'ordered_turnover' not in fields_copy:
            fields_copy.append('ordered_turnover')
        if 'ordered_margin' not in fields_copy:
            fields_copy.append('ordered_margin')
        if 'recorded_turnover' not in fields_copy:
            fields_copy.append('recorded_turnover')
        if 'recorded_margin' not in fields_copy:
            fields_copy.append('recorded_margin')
        if 'total_margin' not in fields_copy:
            fields_copy.append('total_margin')
        if 'ordered_turnover_objective' not in fields_copy:
            fields_copy.append('ordered_turnover_objective')
        if 'previous_recorded_turnover' not in fields_copy:
            fields_copy.append('previous_recorded_turnover')
        res = super(OFCRMFunnelConversion4, self).read_group(
            domain, fields_copy, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'quotation_rate' in fields_copy:
                if 'quotation_nb' in line and line['quotation_nb'] is not None and line.get('opportunity_nb', False):
                    line['quotation_rate'] = \
                        ('%.2f' % (round(100.0 * line['quotation_nb'] / line['opportunity_nb'], 2))).replace('.', ',')
                else:
                    line['quotation_rate'] = "N/E"
            if 'order_rate' in fields_copy:
                if 'order_nb' in line and line['order_nb'] is not None and line.get('quotation_nb', False):
                    line['order_rate'] = ('%.2f' % (round(100.0 * line['order_nb'] / line['quotation_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['order_rate'] = "N/E"
            if 'turnover_rate' in fields_copy:
                if 'total_turnover' in line and line['total_turnover'] is not None and \
                        line.get('quotation_amount', False):
                    line['turnover_rate'] = \
                        ('%.2f' % (round(100.0 * line['total_turnover'] / line['quotation_amount'], 2))).\
                        replace('.', ',')
                else:
                    line['turnover_rate'] = "N/E"
            if 'quotation_cart' in fields_copy:
                if 'total_turnover' in line and line['total_turnover'] is not None and line.get('quotation_nb', False):
                    line['quotation_cart'] = ('%.2f' % (round(line['total_turnover'] / line['quotation_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['quotation_cart'] = "N/E"
            if 'sale_cart' in fields_copy:
                if 'total_turnover' in line and line['total_turnover'] is not None and line.get('order_nb', False):
                    line['sale_cart'] = ('%.2f' % (round(line['total_turnover'] / line['order_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['sale_cart'] = "N/E"
            if 'lost_cart' in fields_copy:
                if 'lost_turnover' in line and line['lost_turnover'] is not None and \
                        line.get('lost_quotation_nb', False):
                    line['lost_cart'] = ('%.2f' % (round(line['lost_turnover'] / line['lost_quotation_nb'], 2))).\
                        replace('.', ',')
                else:
                    line['lost_cart'] = "N/E"
            if 'ordered_margin_percent' in fields_copy:
                if 'ordered_turnover' in line and line['ordered_turnover'] is not None and \
                        'ordered_margin' in line and line['ordered_margin'] is not None and \
                        line.get('ordered_turnover', False):
                    line['ordered_margin_percent'] = \
                        ('%.2f' %
                         (round(100 *
                                (1 - (line['ordered_turnover'] - line['ordered_margin']) / line['ordered_turnover']),
                                2))).replace('.', ',')
                else:
                    line['ordered_margin_percent'] = "N/E"
            if 'recorded_margin_percent' in fields_copy:
                if 'recorded_turnover' in line and line['recorded_turnover'] is not None and \
                        'recorded_margin' in line and line['recorded_margin'] is not None and \
                        line.get('recorded_turnover', False):
                    line['recorded_margin_percent'] = \
                        ('%.2f' %
                         (round(100 *
                                (1 - (line['recorded_turnover'] - line['recorded_margin']) / line['recorded_turnover']),
                                2))).replace('.', ',')
                else:
                    line['recorded_margin_percent'] = "N/E"
            if 'total_margin_percent' in fields_copy:
                if 'total_turnover' in line and line['total_turnover'] is not None and 'total_margin' in line and \
                        line['total_margin'] is not None and line.get('total_turnover', False):
                    line['total_margin_percent'] = \
                        ('%.2f' %
                         (round(100 *
                                (1 - (line['total_turnover'] - line['total_margin']) / line['total_turnover']),
                                2))).replace('.', ',')
                else:
                    line['total_margin_percent'] = "N/E"
            if 'rest_to_do' in fields_copy:
                if 'total_turnover' in line and line['total_turnover'] is not None and \
                        line.get('ordered_turnover_objective', False):
                    line['rest_to_do'] = \
                        ('%.2f' % (round(100.0 * line['total_turnover'] / line['ordered_turnover_objective'], 2))).\
                        replace('.', ',')
                else:
                    line['rest_to_do'] = "N/E"
            if 'total_turnover_comparison' in fields_copy:
                if 'total_turnover' in line and line['total_turnover'] is not None and \
                        line.get('previous_recorded_turnover', False):
                    line['total_turnover_comparison'] = \
                        ('%.2f' % (round(100.0 * line['total_turnover'] / line['previous_recorded_turnover'], 2))).\
                        replace('.', ',')
                else:
                    line['total_turnover_comparison'] = "N/E"

        return res

    @api.model
    def export_to_excel_and_send(self):
        # Récupèration du filtre par défaut
        default_filter = self.env['ir.filters'].search(
            [('model_id', '=', self._name), ('user_id', '=', False), ('is_default', '=', True)], limit=1)
        if default_filter:
            # Calcul des données de la vue pivot
            context = literal_eval(default_filter.context)
            groupby_param = []
            data = dict()
            eval_context = {'date': date, 'relativedelta': relativedelta, 'context_today': date.today}
            data['TOTAL_DATA'] = self.read_group(
                domain=safe_eval(default_filter.domain, eval_context), fields=context['pivot_measures'], groupby=[],
                lazy=False)
            for groupby in context['pivot_row_groupby']:
                groupby_param.append(groupby)
                data[groupby] = self.read_group(
                    domain=safe_eval(default_filter.domain, eval_context),
                    fields=context['pivot_measures'] + groupby_param, groupby=groupby_param, lazy=False)

            # Création du fichier Excel

            # Ouverture du workbook
            fp = StringIO()
            workbook = xlsxwriter.Workbook(fp, {'in_memory': True})

            # Création de la page
            worksheet = workbook.add_worksheet(u"Suivi quotidien")

            # Initialisation des colonnes
            worksheet.set_column(0, 0, 23)
            worksheet.set_column(1, len(literal_eval(default_filter.context)['pivot_measures']), 10)

            # Styles
            title_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'left',
                'text_wrap': False,
                'bold': True,
                'font_name': "Arial",
                'font_size': 18,
            })

            column_header_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'center',
                'text_wrap': True,
                'border': 1,
                'bold': True,
                'font_name': "Arial",
                'font_size': 10,
                'bg_color': '#FFFF99',
            })

            even_column_categ_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'right',
                'text_wrap': True,
                'border': 1,
                'bold': True,
                'font_name': "Arial",
                'font_size': 10,
                'bg_color': '#FFFF99',
                'num_format': '# ### ##0',
            })

            odd_column_categ_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'right',
                'text_wrap': True,
                'border': 1,
                'bold': True,
                'font_name': "Arial",
                'font_size': 10,
                'bg_color': '#FFFF00',
                'num_format': '# ### ##0',
            })

            last_level_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'right',
                'text_wrap': True,
                'border': 1,
                'font_name': "Arial",
                'font_size': 10,
                'num_format': '# ### ##0',
            })

            even_line_header_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'left',
                'text_wrap': False,
                'border': 1,
                'bold': True,
                'font_name': "Arial",
                'font_size': 10,
                'bg_color': '#FFFF99',
            })

            odd_line_header_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'left',
                'text_wrap': False,
                'border': 1,
                'bold': True,
                'font_name': "Arial",
                'font_size': 10,
                'bg_color': '#FFFF00',
            })

            last_level_line_header_style = workbook.add_format({
                'valign': 'vcenter',
                'align': 'left',
                'text_wrap': False,
                'border': 1,
                'bold': True,
                'font_name': "Arial",
                'font_size': 10,
            })

            # Ajout des lignes

            def write_row(rdata, line_num, style):
                column_num = 1
                for m in literal_eval(default_filter.context)['pivot_measures']:
                    f = self.env['ir.model.fields'].search([('model', '=', self._name), ('name', '=', m)], limit=1)
                    if f:
                        worksheet.write(line_num, column_num, rdata.get(m), style)
                        column_num += 1

            # En-tête

            worksheet.set_row(0, 25)
            worksheet.merge_range(
                0, 0, 0, 3, u"Export suivi quotidien du %s" % date.today().strftime('%d/%m/%Y'), title_style)
            line_number = 2
            worksheet.set_row(line_number, 50)
            i = 1
            for measure in literal_eval(default_filter.context)['pivot_measures']:
                field = self.env['ir.model.fields'].search(
                    [('model', '=', self._name), ('name', '=', measure)], limit=1)
                if field:
                    worksheet.write(line_number, i, field.field_description, column_header_style)
                    i += 1

            # Ligne de total

            line_number += 1
            worksheet.write(line_number, 0, u"Total", even_line_header_style)
            write_row(data['TOTAL_DATA'][0], line_number, even_column_categ_style)

            # Données

            groupby_list = context['pivot_row_groupby']
            domain = dict()
            line_number_param = [4]

            def write_children(data_param, groupby_field, domain_param):
                groupby_index = groupby_list.index(groupby_field)
                if len(groupby_list) > groupby_index + 1:
                    for child_row_data in data_param.get(groupby_list[groupby_index + 1]):
                        is_child = False
                        for key in domain_param:
                            if key in child_row_data and child_row_data[key] != domain_param[key]:
                                break
                        else:
                            is_child = True
                        if is_child:
                            if len(groupby_list) == groupby_index + 2:
                                header_style = last_level_line_header_style
                                data_style = last_level_style
                            elif ((groupby_index + 2) % 2) == 0:
                                header_style = even_line_header_style
                                data_style = even_column_categ_style
                            else:
                                header_style = odd_line_header_style
                                data_style = odd_column_categ_style

                            worksheet.write(
                                line_number_param[0], 0,
                                ('    ' * (groupby_index + 2)) + (child_row_data[groupby_list[groupby_index + 1]] and
                                                                  child_row_data[groupby_list[groupby_index + 1]][1] or
                                                                  u"Indéfini"),
                                header_style)
                            write_row(child_row_data, line_number_param[0], data_style)
                            line_number_param[0] += 1
                            new_domain_param = domain_param.copy()
                            new_domain_param[groupby_list[groupby_index + 1]] = \
                                child_row_data[groupby_list[groupby_index + 1]]
                            write_children(data_param, groupby_list[groupby_index + 1], new_domain_param)

            for row_data in data.get(groupby_list[0]):
                first_header_style = odd_line_header_style
                first_data_style = odd_column_categ_style
                if len(groupby_list) == 1:
                    first_header_style = last_level_line_header_style
                    first_data_style = last_level_style
                worksheet.write(
                    line_number_param[0], 0,
                    '    ' + (row_data[groupby_list[0]] and row_data[groupby_list[0]][1] or u"Indéfini"),
                    first_header_style)
                write_row(row_data, line_number_param[0], first_data_style)
                line_number_param[0] += 1
                domain[groupby_list[0]] = row_data[groupby_list[0]]
                write_children(data, groupby_list[0], domain)

            # Fermeture du workbook
            workbook.close()
            fp.seek(0)
            file_data = fp.read()
            fp.close()

            # Envoi du mail
            email_template = self.env['ir.model.data'].get_object(
                'of_sale_custom_workflow', 'of_sale_custom_workflow_daily_followup_email_template')
            if email_template:
                file_name = 'suivi_quotidien_%s.xlsx' % date.today().strftime('%Y%m%d')
                mail = self.env['mail.mail'].create({
                    'email_from': email_template.email_from,
                    'email_to': email_template.email_to,
                    'subject': email_template.subject,
                    'body_html': email_template.body_html,
                    'attachment_ids': [(0, 0, {'name': file_name,
                                               'datas_fname': file_name,
                                               'datas': base64.b64encode(file_data)})]
                })
                mail.send()
