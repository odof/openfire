# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools


class OFOperatingDataReport(models.Model):
    _name = 'of.operating.data.report'
    _auto = False
    _description = u"Rapport des données d'exploitation du réseau"
    _rec_name = 'id'

    origin = fields.Selection(
        selection=[('manual', u"Manuelle"), ('connector', u"Connecteur")], string=u"Méthode de création", readonly=True)
    database = fields.Char(string=u"Base de données", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Magasin", readonly=True)
    date = fields.Date(string=u"Date", readonly=True)
    contact_nb = fields.Integer(string=u"Nb contacts", readonly=True)
    previous_contact_nb = fields.Integer(string=u"Nb contacts N-1", readonly=True)
    opportunity_nb = fields.Integer(string=u"Nb opp.", readonly=True)
    previous_opportunity_nb = fields.Integer(string=u"Nb opp. N-1", readonly=True)
    digital_opportunity_nb = fields.Integer(string=u"Nb opp. digitales", readonly=True)
    previous_digital_opportunity_nb = fields.Integer(string=u"Nb opp. digitales N-1", readonly=True)
    quotation_nb = fields.Integer(string=u"Nb devis", readonly=True)
    previous_quotation_nb = fields.Integer(string=u"Nb devis N-1", readonly=True)
    digital_quotation_nb = fields.Integer(string=u"Nb devis digitaux", readonly=True)
    previous_digital_quotation_nb = fields.Integer(string=u"Nb devis digitaux N-1", readonly=True)
    quotation_amount = fields.Float(string=u"Montant devis généré", readonly=True)
    previous_quotation_amount = fields.Float(string=u"Montant devis généré N-1", readonly=True)
    digital_quotation_amount = fields.Float(string=u"Montant devis digitaux généré", readonly=True)
    previous_digital_quotation_amount = fields.Float(string=u"Montant devis digitaux généré N-1", readonly=True)
    current_quotation_amount = fields.Float(string=u"Montant devis en cours", readonly=True)
    sale_nb = fields.Integer(string=u"Nb ventes", readonly=True)
    previous_sale_nb = fields.Integer(string=u"Nb ventes N-1", readonly=True)
    digital_sale_nb = fields.Integer(string=u"Nb ventes digitales", readonly=True)
    previous_digital_sale_nb = fields.Integer(string=u"Nb ventes digitales N-1", readonly=True)
    turnover = fields.Float(string=u"CA €", readonly=True)
    previous_turnover = fields.Float(string=u"CA € N-1", readonly=True)
    digital_turnover = fields.Float(string=u"CA digital €", readonly=True)
    previous_digital_turnover = fields.Float(string=u"CA digital € N-1", readonly=True)
    margin = fields.Float(string=u"Marge €", readonly=True)
    previous_margin = fields.Float(string=u"Marge € N-1", readonly=True)
    invoiced_turnover = fields.Float(string=u"CA facturé €", readonly=True)
    previous_invoiced_turnover = fields.Float(string=u"CA facturé € N-1", readonly=True)
    deposit_excl_invoiced_turnover = fields.Float(string=u"CA facturé € (hors acompte)", readonly=True)
    previous_deposit_excl_invoiced_turnover = fields.Float(string=u"CA facturé € (hors acompte) N-1", readonly=True)

    contact_progression = fields.Char(
        string=u"Évol. contacts", compute='_compute_contact_progression', compute_sudo=True, readonly=True)
    opportunity_progression = fields.Char(
        string=u"Évol. opp.", compute='_compute_opportunity_progression', compute_sudo=True,
        readonly=True)
    digital_opportunity_progression = fields.Char(
        string=u"Évol. opp. digitales", compute='_compute_digital_opportunity_progression',
        compute_sudo=True, readonly=True)
    quotation_progression = fields.Char(
        string=u"Évol. devis", compute='_compute_quotation_progression', compute_sudo=True, readonly=True)
    digital_quotation_progression = fields.Char(
        string=u"Évol. devis digitaux", compute='_compute_digital_quotation_progression', compute_sudo=True,
        readonly=True)
    quotation_amount_progression = fields.Char(
        string=u"Évol. montant devis généré", compute='_compute_quotation_amount_progression',
        compute_sudo=True, readonly=True)
    digital_quotation_amount_progression = fields.Char(
        string=u"Évol. montant devis digitaux généré",
        compute='_compute_digital_quotation_amount_progression', compute_sudo=True, readonly=True)
    sale_progression = fields.Char(
        string=u"Évol. ventes", compute='_compute_sale_progression', compute_sudo=True, readonly=True)
    digital_sale_progression = fields.Char(
        string=u"Évol. ventes digitales", compute='_compute_digital_sale_progression', compute_sudo=True,
        readonly=True)
    turnover_progression = fields.Char(
        string=u"Évol. CA €", compute='_compute_turnover_progression', compute_sudo=True, readonly=True)
    digital_turnover_progression = fields.Char(
        string=u"Évol. CA digital €", compute='_compute_digital_turnover_progression', compute_sudo=True,
        readonly=True)
    margin_progression = fields.Char(
        string=u"Évol. marge €", compute='_compute_margin_progression', compute_sudo=True, readonly=True)
    margin_perc = fields.Char(
        string=u"Marge %", compute='_compute_margin_perc', compute_sudo=True, readonly=True)
    previous_margin_perc = fields.Char(
        string=u"Marge % N-1", compute='_compute_previous_margin_perc', compute_sudo=True, readonly=True)
    margin_perc_progression = fields.Char(
        string=u"Évol. marge %", compute='_compute_margin_perc_progression', compute_sudo=True,
        readonly=True)
    average_cart = fields.Char(
        string=u"Panier moyen €", compute='_compute_average_cart', compute_sudo=True, readonly=True)
    previous_average_cart = fields.Char(
        string=u"Panier moyen € N-1", compute='_compute_previous_average_cart', compute_sudo=True, readonly=True)
    avg_cart_progression = fields.Char(
        string=u"Évol. panier moyen €", compute='_compute_avg_cart_progression', compute_sudo=True,
        readonly=True)
    digital_average_cart = fields.Char(
        string=u"Panier moyen digital €", compute='_compute_digital_average_cart', compute_sudo=True, readonly=True)
    previous_digital_average_cart = fields.Char(
        string=u"Panier moyen digital € N-1", compute='_compute_previous_digital_average_cart', compute_sudo=True,
        readonly=True)
    digital_avg_cart_progression = fields.Char(
        string=u"Évol. panier moyen digital €", compute='_compute_digital_avg_cart_progression',
        compute_sudo=True, readonly=True)
    invoiced_turnover_progression = fields.Char(
        string=u"Évol. CA facturé €", compute='_compute_invoiced_turnover_progression', compute_sudo=True,
        readonly=True)
    deposit_excl_invoiced_turnover_progression = fields.Char(
        string=u"Évol. CA facturé € (hors acompte)",
        compute='_compute_deposit_excl_invoiced_turnover_progression', compute_sudo=True, readonly=True)

    digital_turnover_portion = fields.Char(
        string=u"Part CA digital", compute='_compute_digital_turnover_portion', compute_sudo=True,
        readonly=True)
    previous_digital_turnover_portion = fields.Char(
        string=u"Part CA digital N-1", compute='_compute_previous_digital_turnover_portion', compute_sudo=True,
        readonly=True)
    digital_turnover_portion_progression = fields.Char(
        string=u"Évol. part CA digital", compute='_compute_digital_turnover_portion_progression',
        compute_sudo=True, readonly=True)

    quotation_rate = fields.Char(
        string=u"Taux devis sur opportunité", compute='_compute_quotation_rate', compute_sudo=True,
        readonly=True)
    previous_quotation_rate = fields.Char(
        string=u"Taux devis sur opportunité N-1", compute='_compute_previous_quotation_rate', compute_sudo=True,
        readonly=True)
    quotation_rate_progression = fields.Char(
        string=u"Évol. taux devis sur opportunité", compute='_compute_quotation_rate_progression',
        compute_sudo=True, readonly=True)

    realization_rate = fields.Char(
        string=u"Taux concrét. €", compute='_compute_realization_rate', compute_sudo=True,
        readonly=True)
    previous_realization_rate = fields.Char(
        string=u"Taux concrét. € N-1", compute='_compute_previous_realization_rate', compute_sudo=True,
        readonly=True)
    realization_rate_progression = fields.Char(
        string=u"Évol. taux concrét. €", compute='_compute_realization_rate_progression',
        compute_sudo=True, readonly=True)

    digital_realization_rate = fields.Char(
        string=u"Taux concrét. digitale €", compute='_compute_digital_realization_rate', compute_sudo=True,
        readonly=True)
    previous_digital_realization_rate = fields.Char(
        string=u"Taux concrét. digitale € N-1", compute='_compute_previous_digital_realization_rate',
        compute_sudo=True, readonly=True)
    digital_realization_rate_progression = fields.Char(
        string=u"Évol. taux concrét. digitale €",
        compute='_compute_digital_realization_rate_progression', compute_sudo=True, readonly=True)

    volume_realization_rate = fields.Char(
        string=u"Taux concrét. (vol.)", compute='_compute_volume_realization_rate', compute_sudo=True,
        readonly=True)
    previous_volume_realization_rate = fields.Char(
        string=u"Taux concrét. (vol.) N-1", compute='_compute_previous_volume_realization_rate',
        compute_sudo=True, readonly=True)
    volume_realization_rate_progression = fields.Char(
        string=u"Évol. taux concrét. (vol.)",
        compute='_compute_volume_realization_rate_progression', compute_sudo=True, readonly=True)

    volume_digital_realization_rate = fields.Char(
        string=u"Taux concrét. digitale (vol.)", compute='_compute_volume_digital_realization_rate',
        compute_sudo=True, readonly=True)
    previous_volume_digital_realization_rate = fields.Char(
        string=u"Taux concrét. digitale (vol.) N-1",
        compute='_compute_previous_volume_digital_realization_rate', compute_sudo=True, readonly=True)
    volume_digital_realization_rate_progression = fields.Char(
        string=u"Évol. taux concrét. digitale (vol.)",
        compute='_compute_volume_digital_realization_rate_progression', compute_sudo=True, readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_operating_data_report')
        self._cr.execute("""
            CREATE VIEW %s AS (
                %s
                FROM
                    (   %s
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
            )""" % (self._table,
                    self._select(),
                    self._sub_select_n(),
                    self._sub_from_n(),
                    self._sub_where_n(),
                    self._sub_select_n_1(),
                    self._sub_from_n_1(),
                    self._sub_where_n_1(),
                    self._from(),
                    self._where(),
                    self._group_by()))

    def _select(self):
        select_str = """
            SELECT  MAX(T.id)                                               AS id
            ,       T.origin                                                AS origin
            ,       T.database                                              AS database
            ,       T.partner_id                                            AS partner_id
            ,       T.date                                                  AS date
            ,       COALESCE(SUM(T.contact_nb), 0)                          AS contact_nb
            ,       COALESCE(SUM(T.previous_contact_nb), 0)                 AS previous_contact_nb
            ,       COALESCE(SUM(T.opportunity_nb), 0)                      AS opportunity_nb
            ,       COALESCE(SUM(T.previous_opportunity_nb), 0)             AS previous_opportunity_nb
            ,       COALESCE(SUM(T.digital_opportunity_nb), 0)              AS digital_opportunity_nb
            ,       COALESCE(SUM(T.previous_digital_opportunity_nb), 0)     AS previous_digital_opportunity_nb
            ,       COALESCE(SUM(T.quotation_nb), 0)                        AS quotation_nb
            ,       COALESCE(SUM(T.previous_quotation_nb), 0)               AS previous_quotation_nb
            ,       COALESCE(SUM(T.digital_quotation_nb), 0)                AS digital_quotation_nb
            ,       COALESCE(SUM(T.previous_digital_quotation_nb), 0)       AS previous_digital_quotation_nb
            ,       COALESCE(SUM(T.quotation_amount), 0)                    AS quotation_amount
            ,       COALESCE(SUM(T.previous_quotation_amount), 0)           AS previous_quotation_amount
            ,       COALESCE(SUM(T.digital_quotation_amount), 0)            AS digital_quotation_amount
            ,       COALESCE(SUM(T.previous_digital_quotation_amount), 0)   AS previous_digital_quotation_amount
            ,       COALESCE(SUM(T.current_quotation_amount), 0)            AS current_quotation_amount
            ,       COALESCE(SUM(T.sale_nb), 0)                             AS sale_nb
            ,       COALESCE(SUM(T.previous_sale_nb), 0)                    AS previous_sale_nb
            ,       COALESCE(SUM(T.digital_sale_nb), 0)                     AS digital_sale_nb
            ,       COALESCE(SUM(T.previous_digital_sale_nb), 0)            AS previous_digital_sale_nb
            ,       COALESCE(SUM(T.turnover), 0)                            AS turnover
            ,       COALESCE(SUM(T.previous_turnover), 0)                   AS previous_turnover
            ,       COALESCE(SUM(T.digital_turnover), 0)                    AS digital_turnover
            ,       COALESCE(SUM(T.previous_digital_turnover), 0)           AS previous_digital_turnover
            ,       COALESCE(SUM(T.margin), 0)                              AS margin
            ,       COALESCE(SUM(T.previous_margin), 0)                     AS previous_margin
            ,       COALESCE(SUM(T.invoiced_turnover), 0)                   AS invoiced_turnover
            ,       COALESCE(SUM(T.previous_invoiced_turnover), 0)          AS previous_invoiced_turnover
            ,       COALESCE(SUM(T.deposit_excl_invoiced_turnover), 0)      AS deposit_excl_invoiced_turnover
            ,       COALESCE(
                        SUM(T.previous_deposit_excl_invoiced_turnover), 0)  AS previous_deposit_excl_invoiced_turnover
        """
        return select_str

    def _sub_select_n(self):
        sub_select_n_str = """
            SELECT  OOD.id                              AS id
            ,       OOD.origin                          AS origin
            ,       OOD.database                        AS database
            ,       OOD.partner_id                      AS partner_id
            ,       OOD.period                          AS date
            ,       OOD.contact_nb                      AS contact_nb
            ,       0                                   AS previous_contact_nb
            ,       OOD.opportunity_nb                  AS opportunity_nb
            ,       0                                   AS previous_opportunity_nb
            ,       OOD.digital_opportunity_nb          AS digital_opportunity_nb
            ,       0                                   AS previous_digital_opportunity_nb
            ,       OOD.quotation_nb                    AS quotation_nb
            ,       0                                   AS previous_quotation_nb
            ,       OOD.digital_quotation_nb            AS digital_quotation_nb
            ,       0                                   AS previous_digital_quotation_nb
            ,       OOD.quotation_amount                AS quotation_amount
            ,       0                                   AS previous_quotation_amount
            ,       OOD.digital_quotation_amount        AS digital_quotation_amount
            ,       0                                   AS previous_digital_quotation_amount
            ,       OOD.current_quotation_amount        AS current_quotation_amount
            ,       OOD.sale_nb                         AS sale_nb
            ,       0                                   AS previous_sale_nb
            ,       OOD.digital_sale_nb                 AS digital_sale_nb
            ,       0                                   AS previous_digital_sale_nb
            ,       OOD.turnover                        AS turnover
            ,       0                                   AS previous_turnover
            ,       OOD.digital_turnover                AS digital_turnover
            ,       0                                   AS previous_digital_turnover
            ,       OOD.margin                          AS margin
            ,       0                                   AS previous_margin
            ,       OOD.invoiced_turnover               AS invoiced_turnover
            ,       0                                   AS previous_invoiced_turnover
            ,       OOD.deposit_excl_invoiced_turnover  AS deposit_excl_invoiced_turnover
            ,       0                                   AS previous_deposit_excl_invoiced_turnover
        """
        return sub_select_n_str

    def _sub_from_n(self):
        sub_from_n_str = """
            FROM    of_operating_data   OOD
        """
        return sub_from_n_str

    def _sub_where_n(self):
        sub_where_n_str = ""
        return sub_where_n_str

    def _sub_select_n_1(self):
        sub_select_n_1_str = """
            SELECT  10000000 + OOD2.id                              AS id
            ,       OOD2.origin                                     AS origin
            ,       OOD2.database                                   AS database
            ,       OOD2.partner_id                                 AS partner_id
            ,       DATE(
                        EXTRACT(YEAR FROM OOD2.period) + 1 || '-' ||
                        TO_CHAR(OOD2.period, 'MM') || '-01'
            )                                                       AS date
            ,       0                                               AS contact_nb
            ,       OOD2.contact_nb                                 AS previous_contact_nb
            ,       0                                               AS opportunity_nb
            ,       OOD2.opportunity_nb                             AS previous_opportunity_nb
            ,       0                                               AS digital_opportunity_nb
            ,       OOD2.digital_opportunity_nb                     AS previous_digital_opportunity_nb
            ,       0                                               AS quotation_nb
            ,       OOD2.quotation_nb                               AS previous_quotation_nb
            ,       0                                               AS digital_quotation_nb
            ,       OOD2.digital_quotation_nb                       AS previous_digital_quotation_nb
            ,       0                                               AS quotation_amount
            ,       OOD2.quotation_amount                           AS previous_quotation_amount
            ,       0                                               AS digital_quotation_amount
            ,       OOD2.digital_quotation_amount                   AS previous_digital_quotation_amount
            ,       0                                               AS current_quotation_amount
            ,       0                                               AS sale_nb
            ,       OOD2.sale_nb                                    AS previous_sale_nb
            ,       0                                               AS digital_sale_nb
            ,       OOD2.digital_sale_nb                            AS previous_digital_sale_nb
            ,       0                                               AS turnover
            ,       OOD2.turnover                                   AS previous_turnover
            ,       0                                               AS digital_turnover
            ,       OOD2.digital_turnover                           AS previous_digital_turnover
            ,       0                                               AS margin
            ,       OOD2.margin                                     AS previous_margin
            ,       0                                               AS invoiced_turnover
            ,       OOD2.invoiced_turnover                          AS previous_invoiced_turnover
            ,       0                                               AS deposit_excl_invoiced_turnover
            ,       OOD2.deposit_excl_invoiced_turnover             AS previous_deposit_excl_invoiced_turnover
        """
        return sub_select_n_1_str

    def _sub_from_n_1(self):
        sub_from_n_1_str = """
            FROM    of_operating_data   OOD2
        """
        return sub_from_n_1_str

    def _sub_where_n_1(self):
        sub_where_n_1_str = ""
        return sub_where_n_1_str

    def _from(self):
        from_str = ""
        return from_str

    def _where(self):
        where_str = ""
        return where_str

    def _group_by(self):
        group_str = """
            GROUP BY    T.origin
            ,           T.database
            ,           T.partner_id
            ,           T.date
        """
        return group_str

    @api.multi
    def _compute_contact_progression(self):
        for rec in self:
            if rec.previous_contact_nb != 0:
                rec.contact_progression = '%.2f %%' % \
                    (100.0 * (rec.contact_nb - rec.previous_contact_nb) / rec.previous_contact_nb)
            else:
                rec.contact_progression = "N/A"

    @api.multi
    def _compute_opportunity_progression(self):
        for rec in self:
            if rec.previous_opportunity_nb != 0:
                rec.opportunity_progression = '%.2f %%' % \
                    (100.0 * (rec.opportunity_nb - rec.previous_opportunity_nb) / rec.previous_opportunity_nb)
            else:
                rec.opportunity_progression = "N/A"

    @api.multi
    def _compute_digital_opportunity_progression(self):
        for rec in self:
            if rec.previous_digital_opportunity_nb != 0:
                rec.digital_opportunity_progression = '%.2f %%' % \
                    (100.0 * (rec.digital_opportunity_nb - rec.previous_digital_opportunity_nb) /
                        rec.previous_digital_opportunity_nb)
            else:
                rec.digital_opportunity_progression = "N/A"

    @api.multi
    def _compute_quotation_progression(self):
        for rec in self:
            if rec.previous_quotation_nb != 0:
                rec.quotation_progression = '%.2f %%' % \
                    (100.0 * (rec.quotation_nb - rec.previous_quotation_nb) / rec.previous_quotation_nb)
            else:
                rec.quotation_progression = "N/A"

    @api.multi
    def _compute_digital_quotation_progression(self):
        for rec in self:
            if rec.previous_digital_quotation_nb != 0:
                rec.digital_quotation_progression = '%.2f %%' % \
                    (100.0 * (rec.digital_quotation_nb - rec.previous_digital_quotation_nb) /
                        rec.previous_digital_quotation_nb)
            else:
                rec.digital_quotation_progression = "N/A"

    @api.multi
    def _compute_quotation_amount_progression(self):
        for rec in self:
            if rec.previous_quotation_amount != 0:
                rec.quotation_amount_progression = '%.2f %%' % \
                    (100.0 * (rec.quotation_amount - rec.previous_quotation_amount) / rec.previous_quotation_amount)
            else:
                rec.quotation_amount_progression = "N/A"

    @api.multi
    def _compute_digital_quotation_amount_progression(self):
        for rec in self:
            if rec.previous_digital_quotation_amount != 0:
                rec.digital_quotation_amount_progression = '%.2f %%' % \
                    (100.0 * (rec.digital_quotation_amount - rec.previous_digital_quotation_amount) /
                        rec.previous_digital_quotation_amount)
            else:
                rec.digital_quotation_amount_progression = "N/A"

    @api.multi
    def _compute_sale_progression(self):
        for rec in self:
            if rec.previous_sale_nb != 0:
                rec.sale_progression = '%.2f %%' % \
                    (100.0 * (rec.sale_nb - rec.previous_sale_nb) / rec.previous_sale_nb)
            else:
                rec.sale_progression = "N/A"

    @api.multi
    def _compute_digital_sale_progression(self):
        for rec in self:
            if rec.previous_digital_sale_nb != 0:
                rec.digital_sale_progression = '%.2f %%' % \
                    (100.0 * (rec.digital_sale_nb - rec.previous_digital_sale_nb) / rec.previous_digital_sale_nb)
            else:
                rec.digital_sale_progression = "N/A"

    @api.multi
    def _compute_turnover_progression(self):
        for rec in self:
            if rec.previous_turnover != 0:
                rec.turnover_progression = '%.2f %%' % \
                    (100.0 * (rec.turnover - rec.previous_turnover) / rec.previous_turnover)
            else:
                rec.turnover_progression = "N/A"

    @api.multi
    def _compute_digital_turnover_progression(self):
        for rec in self:
            if rec.previous_digital_turnover != 0:
                rec.digital_turnover_progression = '%.2f %%' % \
                    (100.0 * (rec.digital_turnover - rec.previous_digital_turnover) / rec.previous_digital_turnover)
            else:
                rec.digital_turnover_progression = "N/A"

    @api.multi
    def _compute_margin_progression(self):
        for rec in self:
            if rec.previous_margin != 0:
                rec.margin_progression = '%.2f %%' % \
                    (100.0 * (rec.margin - rec.previous_margin) / rec.previous_margin)
            else:
                rec.margin_progression = "N/A"

    @api.multi
    def _compute_margin_perc(self):
        for rec in self:
            if rec.turnover != 0:
                rec.margin_perc = '%.2f' % (100.0 * rec.margin / rec.turnover)
            else:
                rec.margin_perc = "N/A"

    @api.multi
    def _compute_previous_margin_perc(self):
        for rec in self:
            if rec.previous_turnover != 0:
                rec.previous_margin_perc = '%.2f' % (100.0 * rec.previous_margin / rec.previous_turnover)
            else:
                rec.previous_margin_perc = "N/A"

    @api.multi
    def _compute_margin_perc_progression(self):
        for rec in self:
            if rec.previous_margin != 0 and rec.previous_turnover != 0:
                rec.margin_perc_progression = '%.2f %%' % \
                    (100.0 * ((rec.margin / rec.turnover) - (rec.previous_margin / rec.previous_turnover)) /
                        (rec.previous_margin / rec.previous_turnover))
            else:
                rec.margin_perc_progression = "N/A"

    @api.multi
    def _compute_average_cart(self):
        for rec in self:
            if rec.sale_nb != 0:
                rec.average_cart = '%.2f' % (rec.turnover / rec.sale_nb)
            else:
                rec.average_cart = "N/A"

    @api.multi
    def _compute_previous_average_cart(self):
        for rec in self:
            if rec.previous_sale_nb != 0:
                rec.previous_average_cart = '%.2f' % (rec.previous_turnover / rec.previous_sale_nb)
            else:
                rec.previous_average_cart = "N/A"

    @api.multi
    def _compute_avg_cart_progression(self):
        for rec in self:
            if rec.previous_turnover != 0 and rec.previous_sale_nb != 0:
                rec.avg_cart_progression = '%.2f %%' % \
                    (100.0 * ((rec.turnover / rec.sale_nb) - (rec.previous_turnover / rec.previous_sale_nb)) /
                        (rec.previous_turnover / rec.previous_sale_nb))
            else:
                rec.avg_cart_progression = "N/A"

    @api.multi
    def _compute_digital_average_cart(self):
        for rec in self:
            if rec.digital_sale_nb != 0:
                rec.digital_average_cart = '%.2f' % (rec.digital_turnover / rec.digital_sale_nb)
            else:
                rec.digital_average_cart = "N/A"

    @api.multi
    def _compute_previous_digital_average_cart(self):
        for rec in self:
            if rec.previous_digital_sale_nb != 0:
                rec.previous_digital_average_cart = '%.2f' % \
                    (rec.previous_digital_turnover / rec.previous_digital_sale_nb)
            else:
                rec.previous_digital_average_cart = "N/A"

    @api.multi
    def _compute_digital_avg_cart_progression(self):
        for rec in self:
            if rec.previous_digital_turnover != 0 and rec.previous_digital_sale_nb != 0:
                rec.digital_avg_cart_progression = '%.2f %%' % \
                    (100.0 * ((rec.digital_turnover / rec.digital_sale_nb) -
                              (rec.previous_digital_turnover / rec.previous_digital_sale_nb)) /
                        (rec.previous_digital_turnover / rec.previous_digital_sale_nb))
            else:
                rec.digital_avg_cart_progression = "N/A"

    @api.multi
    def _compute_invoiced_turnover_progression(self):
        for rec in self:
            if rec.previous_invoiced_turnover != 0:
                rec.invoiced_turnover_progression = '%.2f %%' % \
                    (100.0 * (rec.invoiced_turnover - rec.previous_invoiced_turnover) / rec.previous_invoiced_turnover)
            else:
                rec.invoiced_turnover_progression = "N/A"

    @api.multi
    def _compute_deposit_excl_invoiced_turnover_progression(self):
        for rec in self:
            if rec.previous_deposit_excl_invoiced_turnover != 0:
                rec.deposit_excl_invoiced_turnover_progression = '%.2f %%' % \
                    (100.0 * (rec.deposit_excl_invoiced_turnover - rec.previous_deposit_excl_invoiced_turnover) /
                        rec.previous_deposit_excl_invoiced_turnover)
            else:
                rec.deposit_excl_invoiced_turnover_progression = "N/A"

    @api.multi
    def _compute_digital_turnover_portion(self):
        for rec in self:
            if rec.turnover != 0:
                rec.digital_turnover_portion = '%.2f %%' % (100.0 * rec.digital_turnover / rec.turnover)
            else:
                rec.digital_turnover_portion = "N/A"

    @api.multi
    def _compute_previous_digital_turnover_portion(self):
        for rec in self:
            if rec.previous_turnover != 0:
                rec.previous_digital_turnover_portion = '%.2f %%' % \
                    (100.0 * rec.previous_digital_turnover / rec.previous_turnover)
            else:
                rec.previous_digital_turnover_portion = "N/A"

    @api.multi
    def _compute_digital_turnover_portion_progression(self):
        for rec in self:
            if rec.previous_digital_turnover != 0 and rec.previous_turnover != 0:
                rec.digital_turnover_portion_progression = '%.2f %%' % \
                    (100.0 * ((rec.digital_turnover / rec.turnover) -
                              (rec.previous_digital_turnover / rec.previous_turnover)) /
                        (rec.previous_digital_turnover / rec.previous_turnover))
            else:
                rec.digital_turnover_portion_progression = "N/A"

    @api.multi
    def _compute_quotation_rate(self):
        for rec in self:
            if rec.opportunity_nb != 0:
                rec.quotation_rate = '%.2f %%' % (100.0 * rec.quotation_nb / rec.opportunity_nb)
            else:
                rec.quotation_rate = "N/A"

    @api.multi
    def _compute_previous_quotation_rate(self):
        for rec in self:
            if rec.previous_opportunity_nb != 0:
                rec.previous_quotation_rate = '%.2f %%' % \
                    (100.0 * rec.previous_quotation_nb / rec.previous_opportunity_nb)
            else:
                rec.previous_quotation_rate = "N/A"

    @api.multi
    def _compute_quotation_rate_progression(self):
        for rec in self:
            if rec.previous_quotation_nb != 0 and rec.previous_opportunity_nb != 0:
                rec.quotation_rate_progression = '%.2f %%' % \
                    (100.0 * ((rec.quotation_nb / rec.opportunity_nb) -
                              (rec.previous_quotation_nb / rec.previous_opportunity_nb)) /
                        (rec.previous_quotation_nb / rec.previous_opportunity_nb))
            else:
                rec.quotation_rate_progression = "N/A"

    @api.multi
    def _compute_realization_rate(self):
        for rec in self:
            if rec.quotation_amount != 0:
                rec.realization_rate = '%.2f %%' % (100.0 * rec.turnover / rec.quotation_amount)
            else:
                rec.realization_rate = "N/A"

    @api.multi
    def _compute_previous_realization_rate(self):
        for rec in self:
            if rec.previous_quotation_amount != 0:
                rec.previous_realization_rate = '%.2f %%' % \
                    (100.0 * rec.previous_turnover / rec.previous_quotation_amount)
            else:
                rec.previous_realization_rate = "N/A"

    @api.multi
    def _compute_realization_rate_progression(self):
        for rec in self:
            if rec.previous_turnover != 0 and rec.previous_quotation_amount != 0:
                rec.realization_rate_progression = '%.2f %%' % \
                    (100.0 * ((rec.turnover / rec.quotation_amount) -
                              (rec.previous_turnover / rec.previous_quotation_amount)) /
                        (rec.previous_turnover / rec.previous_quotation_amount))
            else:
                rec.realization_rate_progression = "N/A"

    @api.multi
    def _compute_digital_realization_rate(self):
        for rec in self:
            if rec.digital_quotation_amount != 0:
                rec.digital_realization_rate = '%.2f %%' % \
                    (100.0 * rec.digital_turnover / rec.digital_quotation_amount)
            else:
                rec.digital_realization_rate = "N/A"

    @api.multi
    def _compute_previous_digital_realization_rate(self):
        for rec in self:
            if rec.previous_digital_quotation_amount != 0:
                rec.previous_digital_realization_rate = '%.2f %%' % \
                    (100.0 * rec.previous_digital_turnover / rec.previous_digital_quotation_amount)
            else:
                rec.previous_digital_realization_rate = "N/A"

    @api.multi
    def _compute_digital_realization_rate_progression(self):
        for rec in self:
            if rec.previous_digital_turnover != 0 and rec.previous_digital_quotation_amount != 0:
                rec.digital_realization_rate_progression = '%.2f %%' % \
                    (100.0 * ((rec.digital_turnover / rec.digital_quotation_amount) -
                              (rec.previous_digital_turnover / rec.previous_digital_quotation_amount)) /
                        (rec.previous_digital_turnover / rec.previous_digital_quotation_amount))
            else:
                rec.digital_realization_rate_progression = "N/A"

    @api.multi
    def _compute_volume_realization_rate(self):
        for rec in self:
            if rec.quotation_nb != 0:
                rec.volume_realization_rate = '%.2f %%' % (100.0 * rec.sale_nb / rec.quotation_nb)
            else:
                rec.volume_realization_rate = "N/A"

    @api.multi
    def _compute_previous_volume_realization_rate(self):
        for rec in self:
            if rec.previous_quotation_nb != 0:
                rec.previous_volume_realization_rate = '%.2f %%' % \
                    (100.0 * rec.previous_sale_nb / rec.previous_quotation_nb)
            else:
                rec.previous_volume_realization_rate = "N/A"

    @api.multi
    def _compute_volume_realization_rate_progression(self):
        for rec in self:
            if rec.previous_sale_nb != 0 and rec.previous_quotation_nb != 0:
                rec.volume_realization_rate_progression = '%.2f %%' % \
                    (100.0 * ((rec.sale_nb / rec.quotation_nb) - (rec.previous_sale_nb / rec.previous_quotation_nb)) /
                        (rec.previous_sale_nb / rec.previous_quotation_nb))
            else:
                rec.volume_realization_rate_progression = "N/A"

    @api.multi
    def _compute_volume_digital_realization_rate(self):
        for rec in self:
            if rec.digital_quotation_nb != 0:
                rec.volume_digital_realization_rate = '%.2f %%' % \
                    (100.0 * rec.digital_sale_nb / rec.digital_quotation_nb)
            else:
                rec.volume_digital_realization_rate = "N/A"

    @api.multi
    def _compute_previous_volume_digital_realization_rate(self):
        for rec in self:
            if rec.previous_digital_quotation_nb != 0:
                rec.previous_volume_digital_realization_rate = '%.2f %%' % \
                    (100.0 * rec.previous_digital_sale_nb / rec.previous_digital_quotation_nb)
            else:
                rec.previous_volume_digital_realization_rate = "N/A"

    @api.multi
    def _compute_volume_digital_realization_rate_progression(self):
        for rec in self:
            if rec.previous_digital_sale_nb != 0 and rec.previous_digital_quotation_nb != 0:
                rec.volume_digital_realization_rate_progression = '%.2f %%' % \
                    (100.0 * ((rec.digital_sale_nb / rec.digital_quotation_nb) -
                              (rec.previous_digital_sale_nb / rec.previous_digital_quotation_nb)) /
                        (rec.previous_digital_sale_nb / rec.previous_digital_quotation_nb))
            else:
                rec.volume_digital_realization_rate_progression = "N/A"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        fields_copy = fields
        if 'contact_nb' not in fields_copy:
            fields_copy.append('contact_nb')
        if 'previous_contact_nb' not in fields_copy:
            fields_copy.append('previous_contact_nb')
        if 'opportunity_nb' not in fields_copy:
            fields_copy.append('opportunity_nb')
        if 'previous_opportunity_nb' not in fields_copy:
            fields_copy.append('previous_opportunity_nb')
        if 'digital_opportunity_nb' not in fields_copy:
            fields_copy.append('digital_opportunity_nb')
        if 'previous_digital_opportunity_nb' not in fields_copy:
            fields_copy.append('previous_digital_opportunity_nb')
        if 'quotation_nb' not in fields_copy:
            fields_copy.append('quotation_nb')
        if 'previous_quotation_nb' not in fields_copy:
            fields_copy.append('previous_quotation_nb')
        if 'digital_quotation_nb' not in fields_copy:
            fields_copy.append('digital_quotation_nb')
        if 'previous_digital_quotation_nb' not in fields_copy:
            fields_copy.append('previous_digital_quotation_nb')
        if 'quotation_amount' not in fields_copy:
            fields_copy.append('quotation_amount')
        if 'previous_quotation_amount' not in fields_copy:
            fields_copy.append('previous_quotation_amount')
        if 'digital_quotation_amount' not in fields_copy:
            fields_copy.append('digital_quotation_amount')
        if 'previous_digital_quotation_amount' not in fields_copy:
            fields_copy.append('previous_digital_quotation_amount')
        if 'sale_nb' not in fields_copy:
            fields_copy.append('sale_nb')
        if 'previous_sale_nb' not in fields_copy:
            fields_copy.append('previous_sale_nb')
        if 'digital_sale_nb' not in fields_copy:
            fields_copy.append('digital_sale_nb')
        if 'previous_digital_sale_nb' not in fields_copy:
            fields_copy.append('previous_digital_sale_nb')
        if 'turnover' not in fields_copy:
            fields_copy.append('turnover')
        if 'previous_turnover' not in fields_copy:
            fields_copy.append('previous_turnover')
        if 'digital_turnover' not in fields_copy:
            fields_copy.append('digital_turnover')
        if 'previous_digital_turnover' not in fields_copy:
            fields_copy.append('previous_digital_turnover')
        if 'margin' not in fields_copy:
            fields_copy.append('margin')
        if 'previous_margin' not in fields_copy:
            fields_copy.append('previous_margin')
        if 'invoiced_turnover' not in fields_copy:
            fields_copy.append('invoiced_turnover')
        if 'previous_invoiced_turnover' not in fields_copy:
            fields_copy.append('previous_invoiced_turnover')
        if 'deposit_excl_invoiced_turnover' not in fields_copy:
            fields_copy.append('deposit_excl_invoiced_turnover')
        if 'previous_deposit_excl_invoiced_turnover' not in fields_copy:
            fields_copy.append('previous_deposit_excl_invoiced_turnover')

        res = super(OFOperatingDataReport, self).read_group(
            domain, fields_copy, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        for line in res:
            if 'contact_progression' in fields_copy:
                if 'contact_nb' in line and line['contact_nb'] is not None and line.get('previous_contact_nb', False):
                    line['contact_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['contact_nb'] - line['previous_contact_nb']) /
                            line['previous_contact_nb'], 2))).replace('.', ',')
                else:
                    line['contact_progression'] = "N/A"
            if 'opportunity_progression' in fields_copy:
                if 'opportunity_nb' in line and line['opportunity_nb'] is not None and \
                        line.get('previous_opportunity_nb', False):
                    line['opportunity_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['opportunity_nb'] - line['previous_opportunity_nb']) /
                            line['previous_opportunity_nb'], 2))).replace('.', ',')
                else:
                    line['opportunity_progression'] = "N/A"
            if 'digital_opportunity_progression' in fields_copy:
                if 'digital_opportunity_nb' in line and line['digital_opportunity_nb'] is not None and \
                        line.get('previous_digital_opportunity_nb', False):
                    line['digital_opportunity_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['digital_opportunity_nb'] - line['previous_digital_opportunity_nb']) /
                            line['previous_digital_opportunity_nb'], 2))).replace('.', ',')
                else:
                    line['digital_opportunity_progression'] = "N/A"
            if 'quotation_progression' in fields_copy:
                if 'quotation_nb' in line and line['quotation_nb'] is not None and \
                        line.get('previous_quotation_nb', False):
                    line['quotation_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['quotation_nb'] - line['previous_quotation_nb']) /
                            line['previous_quotation_nb'], 2))).replace('.', ',')
                else:
                    line['quotation_progression'] = "N/A"
            if 'digital_quotation_progression' in fields_copy:
                if 'digital_quotation_nb' in line and line['digital_quotation_nb'] is not None and \
                        line.get('previous_digital_quotation_nb', False):
                    line['digital_quotation_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['digital_quotation_nb'] - line['previous_digital_quotation_nb']) /
                            line['previous_digital_quotation_nb'], 2))).replace('.', ',')
                else:
                    line['digital_quotation_progression'] = "N/A"
            if 'quotation_amount_progression' in fields_copy:
                if 'quotation_amount' in line and line['quotation_amount'] is not None and \
                        line.get('previous_quotation_amount', False):
                    line['quotation_amount_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['quotation_amount'] - line['previous_quotation_amount']) /
                            line['previous_quotation_amount'], 2))).replace('.', ',')
                else:
                    line['quotation_amount_progression'] = "N/A"
            if 'digital_quotation_amount_progression' in fields_copy:
                if 'digital_quotation_amount' in line and line['digital_quotation_amount'] is not None and \
                        line.get('previous_digital_quotation_amount', False):
                    line['digital_quotation_amount_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['digital_quotation_amount'] - line['previous_digital_quotation_amount']) /
                            line['previous_digital_quotation_amount'], 2))).replace('.', ',')
                else:
                    line['digital_quotation_amount_progression'] = "N/A"
            if 'sale_progression' in fields_copy:
                if 'sale_nb' in line and line['sale_nb'] is not None and \
                        line.get('previous_sale_nb', False):
                    line['sale_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['sale_nb'] - line['previous_sale_nb']) /
                            line['previous_sale_nb'], 2))).replace('.', ',')
                else:
                    line['sale_progression'] = "N/A"
            if 'digital_sale_progression' in fields_copy:
                if 'digital_sale_nb' in line and line['digital_sale_nb'] is not None and \
                        line.get('previous_digital_sale_nb', False):
                    line['digital_sale_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['digital_sale_nb'] - line['previous_digital_sale_nb']) /
                            line['previous_digital_sale_nb'], 2))).replace('.', ',')
                else:
                    line['digital_sale_progression'] = "N/A"
            if 'turnover_progression' in fields_copy:
                if 'turnover' in line and line['turnover'] is not None and \
                        line.get('previous_turnover', False):
                    line['turnover_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['turnover'] - line['previous_turnover']) /
                            line['previous_turnover'], 2))).replace('.', ',')
                else:
                    line['turnover_progression'] = "N/A"
            if 'digital_turnover_progression' in fields_copy:
                if 'digital_turnover' in line and line['digital_turnover'] is not None and \
                        line.get('previous_digital_turnover', False):
                    line['digital_turnover_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['digital_turnover'] - line['previous_digital_turnover']) /
                            line['previous_digital_turnover'], 2))).replace('.', ',')
                else:
                    line['digital_turnover_progression'] = "N/A"
            if 'margin_progression' in fields_copy:
                if 'margin' in line and line['margin'] is not None and \
                        line.get('previous_margin', False):
                    line['margin_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['margin'] - line['previous_margin']) /
                            line['previous_margin'], 2))).replace('.', ',')
                else:
                    line['margin_progression'] = "N/A"
            if 'margin_perc' in fields_copy:
                if 'margin' in line and line['margin'] is not None and line.get('turnover', False):
                    line['margin_perc'] = \
                        ('%.2f' % (round(100.0 * line['margin'] / line['turnover'], 2))).replace('.', ',')
                else:
                    line['margin_perc'] = "N/A"
            if 'previous_margin_perc' in fields_copy:
                if 'previous_margin' in line and line['previous_margin'] is not None and \
                        line.get('previous_turnover', False):
                    line['previous_margin_perc'] = \
                        ('%.2f' % (round(
                            100.0 * line['previous_margin'] / line['previous_turnover'], 2))).replace('.', ',')
                else:
                    line['previous_margin_perc'] = "N/A"
            if 'margin_perc_progression' in fields_copy:
                if 'margin' in line and line['margin'] is not None and line.get('previous_margin', False) and \
                        line.get('turnover', False) and line.get('previous_turnover', False):
                    line['margin_perc_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['margin'] / line['turnover']) -
                                     (line['previous_margin'] / line['previous_turnover'])) /
                            (line['previous_margin'] / line['previous_turnover']), 2))).replace('.', ',')
                else:
                    line['margin_perc_progression'] = "N/A"
            if 'average_cart' in fields_copy:
                if 'turnover' in line and line['turnover'] is not None and line.get('sale_nb', False):
                    line['average_cart'] = \
                        ('%.2f' % (round(line['turnover'] / line['sale_nb'], 2))).replace('.', ',')
                else:
                    line['average_cart'] = "N/A"
            if 'previous_average_cart' in fields_copy:
                if 'previous_turnover' in line and line['previous_turnover'] is not None and \
                        line.get('previous_sale_nb', False):
                    line['previous_average_cart'] = \
                        ('%.2f' % (round(
                            line['previous_turnover'] / line['previous_sale_nb'], 2))).replace('.', ',')
                else:
                    line['previous_average_cart'] = "N/A"
            if 'avg_cart_progression' in fields_copy:
                if 'turnover' in line and line['turnover'] is not None and line.get('previous_turnover', False) and \
                        line.get('sale_nb', False) and line.get('previous_sale_nb', False):
                    line['avg_cart_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['turnover'] / line['sale_nb']) -
                                     (line['previous_turnover'] / line['previous_sale_nb'])) /
                            (line['previous_turnover'] / line['previous_sale_nb']), 2))).replace('.', ',')
                else:
                    line['avg_cart_progression'] = "N/A"
            if 'digital_average_cart' in fields_copy:
                if 'digital_turnover' in line and line['digital_turnover'] is not None and \
                        line.get('digital_sale_nb', False):
                    line['digital_average_cart'] = \
                        ('%.2f' % (round(
                            line['digital_turnover'] / line['digital_sale_nb'], 2))).replace('.', ',')
                else:
                    line['digital_average_cart'] = "N/A"
            if 'previous_digital_average_cart' in fields_copy:
                if 'previous_digital_turnover' in line and line['previous_digital_turnover'] is not None and \
                        line.get('previous_digital_sale_nb', False):
                    line['previous_digital_average_cart'] = \
                        ('%.2f' % (round(
                            line['previous_digital_turnover'] /
                            line['previous_digital_sale_nb'], 2))).replace('.', ',')
                else:
                    line['previous_digital_average_cart'] = "N/A"
            if 'digital_avg_cart_progression' in fields_copy:
                if 'digital_turnover' in line and line['digital_turnover'] is not None and \
                        line.get('previous_digital_turnover', False) and line.get('digital_sale_nb', False) and \
                        line.get('previous_digital_sale_nb', False):
                    line['digital_avg_cart_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['digital_turnover'] / line['digital_sale_nb']) -
                                     (line['previous_digital_turnover'] / line['previous_digital_sale_nb'])) /
                            (line['previous_digital_turnover'] /
                             line['previous_digital_sale_nb']), 2))).replace('.', ',')
                else:
                    line['digital_avg_cart_progression'] = "N/A"
            if 'invoiced_turnover_progression' in fields_copy:
                if 'invoiced_turnover' in line and line['invoiced_turnover'] is not None and \
                        line.get('previous_invoiced_turnover', False):
                    line['invoiced_turnover_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['invoiced_turnover'] - line['previous_invoiced_turnover']) /
                            line['previous_invoiced_turnover'], 2))).replace('.', ',')
                else:
                    line['invoiced_turnover_progression'] = "N/A"
            if 'deposit_excl_invoiced_turnover_progression' in fields_copy:
                if 'deposit_excl_invoiced_turnover' in line and line['deposit_excl_invoiced_turnover'] is not None and \
                        line.get('previous_deposit_excl_invoiced_turnover', False):
                    line['deposit_excl_invoiced_turnover_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * (line['deposit_excl_invoiced_turnover'] -
                                     line['previous_deposit_excl_invoiced_turnover']) /
                            line['previous_deposit_excl_invoiced_turnover'], 2))).replace('.', ',')
                else:
                    line['deposit_excl_invoiced_turnover_progression'] = "N/A"
            if 'digital_turnover_portion' in fields_copy:
                if 'digital_turnover' in line and line['digital_turnover'] is not None and line.get('turnover', False):
                    line['digital_turnover_portion'] = \
                        ('%.2f %%' % (round(100.0 * line['digital_turnover'] / line['turnover'], 2))).replace('.', ',')
                else:
                    line['digital_turnover_portion'] = "N/A"
            if 'previous_digital_turnover_portion' in fields_copy:
                if 'previous_digital_turnover' in line and line['previous_digital_turnover'] is not None and \
                        line.get('previous_turnover', False):
                    line['previous_digital_turnover_portion'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['previous_digital_turnover'] /
                            line['previous_turnover'], 2))).replace('.', ',')
                else:
                    line['previous_digital_turnover_portion'] = "N/A"
            if 'digital_turnover_portion_progression' in fields_copy:
                if 'digital_turnover' in line and line['digital_turnover'] is not None and \
                        line.get('turnover', False) and line.get('previous_turnover', False) and \
                        line.get('previous_digital_turnover', False):
                    line['digital_turnover_portion_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['digital_turnover'] / line['turnover']) -
                                     (line['previous_digital_turnover'] / line['previous_turnover'])) /
                            (line['previous_digital_turnover'] / line['previous_turnover']), 2))).replace('.', ',')
                else:
                    line['digital_turnover_portion_progression'] = "N/A"
            if 'quotation_rate' in fields_copy:
                if 'quotation_nb' in line and line['quotation_nb'] is not None and line.get('opportunity_nb', False):
                    line['quotation_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['quotation_nb'] / line['opportunity_nb'], 2))).replace('.', ',')
                else:
                    line['quotation_rate'] = "N/A"
            if 'previous_quotation_rate' in fields_copy:
                if 'previous_quotation_nb' in line and line['previous_quotation_nb'] is not None and \
                        line.get('previous_quotation_nb', False):
                    line['previous_quotation_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['previous_quotation_nb'] /
                            line['previous_opportunity_nb'], 2))).replace('.', ',')
                else:
                    line['previous_quotation_rate'] = "N/A"
            if 'quotation_rate_progression' in fields_copy:
                if 'quotation_nb' in line and line['quotation_nb'] is not None and \
                        line.get('opportunity_nb', False) and line.get('previous_quotation_nb', False) and \
                        line.get('previous_quotation_nb', False):
                    line['quotation_rate_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['quotation_nb'] / line['opportunity_nb']) -
                                     (line['previous_quotation_nb'] / line['previous_opportunity_nb'])) /
                            (line['previous_quotation_nb'] / line['previous_opportunity_nb']), 2))).replace('.', ',')
                else:
                    line['quotation_rate_progression'] = "N/A"
            if 'realization_rate' in fields_copy:
                if 'turnover' in line and line['turnover'] is not None and line.get('quotation_amount', False):
                    line['realization_rate'] = \
                        ('%.2f %%' % (round(100.0 * line['turnover'] / line['quotation_amount'], 2))).replace('.', ',')
                else:
                    line['realization_rate'] = "N/A"
            if 'previous_realization_rate' in fields_copy:
                if 'previous_turnover' in line and line['previous_turnover'] is not None and \
                        line.get('previous_quotation_amount', False):
                    line['previous_realization_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['previous_turnover'] /
                            line['previous_quotation_amount'], 2))).replace('.', ',')
                else:
                    line['previous_realization_rate'] = "N/A"
            if 'realization_rate_progression' in fields_copy:
                if 'turnover' in line and line['turnover'] is not None and \
                        line.get('quotation_amount', False) and line.get('previous_turnover', False) and \
                        line.get('previous_quotation_amount', False):
                    line['realization_rate_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['turnover'] / line['quotation_amount']) -
                                     (line['previous_turnover'] / line['previous_quotation_amount'])) /
                            (line['previous_turnover'] / line['previous_quotation_amount']), 2))).replace('.', ',')
                else:
                    line['realization_rate_progression'] = "N/A"
            if 'digital_realization_rate' in fields_copy:
                if 'digital_turnover' in line and line['digital_turnover'] is not None and \
                        line.get('digital_quotation_amount', False):
                    line['digital_realization_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['digital_turnover'] / line['digital_quotation_amount'], 2))).replace('.', ',')
                else:
                    line['digital_realization_rate'] = "N/A"
            if 'previous_digital_realization_rate' in fields_copy:
                if 'previous_digital_turnover' in line and line['previous_digital_turnover'] is not None and \
                        line.get('previous_digital_quotation_amount', False):
                    line['previous_digital_realization_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['previous_digital_turnover'] /
                            line['previous_digital_quotation_amount'], 2))).replace('.', ',')
                else:
                    line['previous_digital_realization_rate'] = "N/A"
            if 'digital_realization_rate_progression' in fields_copy:
                if 'digital_turnover' in line and line['digital_turnover'] is not None and \
                        line.get('digital_quotation_amount', False) and \
                        line.get('previous_digital_turnover', False) and \
                        line.get('previous_digital_quotation_amount', False):
                    line['digital_realization_rate_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['digital_turnover'] / line['digital_quotation_amount']) -
                                     (line['previous_digital_turnover'] / line['previous_digital_quotation_amount'])) /
                            (line['previous_digital_turnover'] /
                             line['previous_digital_quotation_amount']), 2))).replace('.', ',')
                else:
                    line['digital_realization_rate_progression'] = "N/A"
            if 'volume_realization_rate' in fields_copy:
                if 'sale_nb' in line and line['sale_nb'] is not None and \
                        line.get('quotation_nb', False):
                    line['volume_realization_rate'] = \
                        ('%.2f %%' % (round(100.0 * line['sale_nb'] / line['quotation_nb'], 2))).replace('.', ',')
                else:
                    line['volume_realization_rate'] = "N/A"
            if 'previous_volume_realization_rate' in fields_copy:
                if 'previous_sale_nb' in line and line['previous_sale_nb'] is not None and \
                        line.get('previous_quotation_nb', False):
                    line['previous_volume_realization_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['previous_sale_nb'] / line['previous_quotation_nb'], 2))).replace('.', ',')
                else:
                    line['previous_volume_realization_rate'] = "N/A"
            if 'volume_realization_rate_progression' in fields_copy:
                if 'sale_nb' in line and line['sale_nb'] is not None and line.get('quotation_nb', False) and \
                        line.get('previous_sale_nb', False) and line.get('previous_quotation_nb', False):
                    line['volume_realization_rate_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['sale_nb'] / line['quotation_nb']) -
                                     (line['previous_sale_nb'] / line['previous_quotation_nb'])) /
                            (line['previous_sale_nb'] / line['previous_quotation_nb']), 2))).replace('.', ',')
                else:
                    line['volume_realization_rate_progression'] = "N/A"
            if 'volume_digital_realization_rate' in fields_copy:
                if 'digital_sale_nb' in line and line['digital_sale_nb'] is not None and \
                        line.get('digital_quotation_nb', False):
                    line['volume_digital_realization_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['digital_sale_nb'] / line['digital_quotation_nb'], 2))).replace('.', ',')
                else:
                    line['volume_digital_realization_rate'] = "N/A"
            if 'previous_volume_digital_realization_rate' in fields_copy:
                if 'previous_digital_sale_nb' in line and line['previous_digital_sale_nb'] is not None and \
                        line.get('previous_digital_quotation_nb', False):
                    line['previous_volume_digital_realization_rate'] = \
                        ('%.2f %%' % (round(
                            100.0 * line['previous_digital_sale_nb'] /
                            line['previous_digital_quotation_nb'], 2))).replace('.', ',')
                else:
                    line['previous_volume_digital_realization_rate'] = "N/A"
            if 'volume_digital_realization_rate_progression' in fields_copy:
                if 'digital_sale_nb' in line and line['digital_sale_nb'] is not None and \
                        line.get('digital_quotation_nb', False) and line.get('previous_digital_sale_nb', False) and \
                        line.get('previous_digital_quotation_nb', False):
                    line['volume_digital_realization_rate_progression'] = \
                        ('%.2f %%' % (round(
                            100.0 * ((line['digital_sale_nb'] / line['digital_quotation_nb']) -
                                     (line['previous_digital_sale_nb'] / line['previous_digital_quotation_nb'])) /
                            (line['previous_digital_sale_nb'] /
                             line['previous_digital_quotation_nb']), 2))).replace('.', ',')
                else:
                    line['volume_digital_realization_rate_progression'] = "N/A"

        return res
