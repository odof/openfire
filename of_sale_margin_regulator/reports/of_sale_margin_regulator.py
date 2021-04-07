# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools


class OFSaleMarginRegulator(models.Model):
    """Régule de marge"""

    _name = 'of.sale.margin.regulator'
    _auto = False
    _description = "Régule de marge"
    _rec_name = 'id'

    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u"Vendeur", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire", readonly=True)
    order_date = fields.Date(string=u"Date de commande", readonly=True)
    custom_confirmation_date = fields.Date(string=u"Date de confirmation", readonly=True)
    confirmation_date = fields.Date(string=u"Date d'enregistrement'", readonly=True)
    invoice_date = fields.Date(string=u"Date de dernière facture", readonly=True)
    invoice_status = fields.Selection([
        ('upselling', u"Opportunité de montée en gamme"),
        ('invoiced', u"Entièrement facturé"),
        ('to invoice', u"À facturer"),
        ('no', u"Rien à facturer")
        ], string=u"État de facturation", readonly=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article")

    presale_cost = fields.Float(string=u"Prix de revient à la confirmation", readonly=True)
    presale_price = fields.Float(string=u"Prix de vente à la confirmation", readonly=True)
    presale_price_variation = fields.Float(string=u"Variation de prix à la confirmation", readonly=True)
    presale_margin = fields.Float(string=u"Marge à la confirmation (€)", readonly=True)
    presale_margin_perc = fields.Char(
        string=u"Marge à la confirmation (%)", compute='_compute_presale_margin_perc', compute_sudo=True, readonly=True)

    sale_cost = fields.Float(string=u"Prix de revient à l'enregistrement", readonly=True)
    sale_price = fields.Float(string=u"Prix de vente à l'enregistrement", readonly=True)
    sale_price_variation = fields.Float(string=u"Variation de prix à l'enregistrement", readonly=True)
    sale_margin = fields.Float(string=u"Marge à l'enregistrement (€)", readonly=True)
    sale_margin_perc = fields.Char(
        string=u"Marge à l'enregistrement (%)", compute='_compute_sale_margin_perc', compute_sudo=True, readonly=True)

    delivered_cost = fields.Float(string=u"Coût livré", readonly=True)
    invoiced_total = fields.Float(string=u"Total HT facturé", readonly=True)

    ordered_real_margin = fields.Float(
        string=u"Marge réelle sur commandé (€)", compute='_compute_ordered_real_margin', compute_sudo=True,
        readonly=True)
    ordered_real_margin_perc = fields.Char(
        string=u"Marge réelle sur commandé (%)", compute='_compute_ordered_real_margin_perc', compute_sudo=True,
        readonly=True)
    invoiced_real_margin = fields.Float(
        string=u"Marge réelle sur facturé (€)", compute='_compute_invoiced_real_margin', compute_sudo=True,
        readonly=True)
    invoiced_real_margin_perc = fields.Char(
        string=u"Marge réelle sur facturé (%)", compute='_compute_invoiced_real_margin_perc', compute_sudo=True,
        readonly=True)

    ordered_real_sale_margin_gap = fields.Float(
        string=u"Écart Marge réelle commandée / Marge à l'enregistrement (€)",
        compute='_compute_ordered_real_sale_margin_gap', compute_sudo=True, readonly=True)
    ordered_real_sale_margin_gap_perc = fields.Char(
        string=u"Écart Marge réelle commandée / Marge à l'enregistrement (%)",
        compute='_compute_ordered_real_sale_margin_gap_perc', compute_sudo=True, readonly=True)
    invoiced_real_sale_margin_gap = fields.Float(
        string=u"Écart Marge réelle facturée / Marge à l'enregistrement (€)",
        compute='_compute_invoiced_real_sale_margin_gap', compute_sudo=True, readonly=True)
    invoiced_real_sale_margin_gap_perc = fields.Char(
        string=u"Écart Marge réelle facturée / Marge à l'enregistrement (%)",
        compute='_compute_invoiced_real_sale_margin_gap_perc', compute_sudo=True, readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_sale_margin_regulator')
        self._cr.execute("""
            CREATE VIEW of_sale_margin_regulator AS (
                    SELECT      SOL.id                                                      AS id
                    ,           SO.id                                                       AS order_id
                    ,           SO.company_id
                    ,           SO.user_id
                    ,           SO.partner_id
                    ,           SO.date_order::timestamp::date                              AS order_date
                    ,           SO.of_custom_confirmation_date::timestamp::date             AS custom_confirmation_date
                    ,           SO.confirmation_date::timestamp::date                       AS confirmation_date
                    ,           SO.invoice_status
                    ,           (   SELECT  MAX(AI2.date_invoice)
                                    FROM    sale_order_line             SOL2
                                    ,       sale_order_line_invoice_rel SOLIR2
                                    ,       account_invoice_line        AIL2
                                    ,       account_invoice             AI2
                                    WHERE   SOL2.order_id               = SO.id
                                    AND     SOLIR2.order_line_id        = SOL2.id
                                    AND     AIL2.id                     = SOLIR2.invoice_line_id
                                    AND     AI2.id                      = AIL2.invoice_id
                                    AND     AI2.state                   IN ('open', 'paid')
                                )                                                           AS invoice_date
                    ,           SOL.product_id
                    ,           SOL.of_presale_cost                                         AS presale_cost
                    ,           SOL.of_presale_price                                        AS presale_price
                    ,           SOL.of_presale_price_variation                              AS presale_price_variation
                    ,           SOL.of_presale_margin                                       AS presale_margin
                    ,           SOL.of_sale_cost                                            AS sale_cost
                    ,           SOL.of_sale_price                                           AS sale_price
                    ,           SOL.of_sale_price_variation                                 AS sale_price_variation
                    ,           SOL.of_sale_margin                                          AS sale_margin
                    ,           MOV.delivered_cost                                          AS delivered_cost
                    ,           INV.invoiced_total                                          AS invoiced_total
                    FROM        sale_order                                                  SO
                    ,           sale_order_line                                             SOL
                    LEFT JOIN   (   SELECT      PO.sale_line_id
                                    ,           SUM(SM.of_unit_cost * SM.product_uom_qty)   AS delivered_cost
                                    FROM        procurement_order                           PO
                                    ,           stock_move                                  SM
                                    WHERE       SM.procurement_id                           = PO.id
                                    AND         SM.state                                    = 'done'
                                    GROUP BY    PO.sale_line_id
                                )                                                           MOV
                        ON      MOV.sale_line_id                                            = SOL.id
                    LEFT JOIN   (   SELECT      SOLIR.order_line_id
                                    ,           SUM(AIL.price_subtotal)     AS invoiced_total
                                    FROM        sale_order_line_invoice_rel SOLIR
                                    ,           account_invoice_line        AIL
                                    ,           account_invoice             AI
                                    WHERE       AIL.id                      = SOLIR.invoice_line_id
                                    AND         AI.id                       = AIL.invoice_id
                                    AND         AI.state                    IN ('open', 'paid')
                                    GROUP BY    SOLIR.order_line_id
                                )                                                           INV
                        ON      INV.order_line_id                                           = SOL.id
                    WHERE       SO.state                                                    IN ('sale', 'done', 'closed')
                    AND         SOL.order_id                                                = SO.id

                    UNION

                    SELECT      100000000 + SM2.id                                          AS id
                    ,           SO2.id                                                      AS order_id
                    ,           SO2.company_id
                    ,           SO2.user_id
                    ,           SO2.partner_id
                    ,           SO2.date_order::timestamp::date                             AS order_date
                    ,           SO2.of_custom_confirmation_date::timestamp::date            AS custom_confirmation_date
                    ,           SO2.confirmation_date::timestamp::date                      AS confirmation_date
                    ,           SO2.invoice_status
                    ,           (   SELECT  MAX(AI3.date_invoice)
                                    FROM    sale_order_line             SOL3
                                    ,       sale_order_line_invoice_rel SOLIR3
                                    ,       account_invoice_line        AIL3
                                    ,       account_invoice             AI3
                                    WHERE   SOL3.order_id               = SO2.id
                                    AND     SOLIR3.order_line_id        = SOL3.id
                                    AND     AIL3.id                     = SOLIR3.invoice_line_id
                                    AND     AI3.id                      = AIL3.invoice_id
                                    AND     AI3.state                   IN ('open', 'paid')
                                )                                                           AS invoice_date
                    ,           SM2.product_id
                    ,           NULL                                                        AS presale_cost
                    ,           NULL                                                        AS presale_price
                    ,           NULL                                                        AS presale_price_variation
                    ,           NULL                                                        AS presale_margin
                    ,           NULL                                                        AS sale_cost
                    ,           NULL                                                        AS sale_price
                    ,           NULL                                                        AS sale_price_variation
                    ,           NULL                                                        AS sale_margin
                    ,           SM2.of_unit_cost * SM2.product_uom_qty                      AS delivered_cost
                    ,           NULL                                                        AS invoiced_total
                    FROM        sale_order                                                  SO2
                    ,           stock_picking                                               SP
                    ,           stock_move                                                  SM2
                    WHERE       SO2.state                                                   IN ('sale', 'done', 'closed')
                    AND         SP.origin                                                   = SO2.name
                    AND         SM2.picking_id                                              = SP.id
                    AND         (   SM2.procurement_id                                      IS NULL
                                OR  EXISTS                                                  (   SELECT  *
                                                                                                FROM    procurement_order   PO2
                                                                                                WHERE   PO2.id              = SM2.procurement_id
                                                                                                AND     PO2.of_sale_comp_id IS NOT NULL
                                                                                            )
                                )

                    UNION

                    SELECT      200000000 + AIL4.id                                         AS id
                    ,           SO3.id                                                      AS order_id
                    ,           SO3.company_id
                    ,           SO3.user_id
                    ,           SO3.partner_id
                    ,           SO3.date_order::timestamp::date                             AS order_date
                    ,           SO3.of_custom_confirmation_date::timestamp::date            AS custom_confirmation_date
                    ,           SO3.confirmation_date::timestamp::date                      AS confirmation_date
                    ,           SO3.invoice_status
                    ,           (   SELECT  MAX(AI5.date_invoice)
                                    FROM    sale_order_line             SOL5
                                    ,       sale_order_line_invoice_rel SOLIR5
                                    ,       account_invoice_line        AIL5
                                    ,       account_invoice             AI5
                                    WHERE   SOL5.order_id               = SO3.id
                                    AND     SOLIR5.order_line_id        = SOL5.id
                                    AND     AIL5.id                     = SOLIR5.invoice_line_id
                                    AND     AI5.id                      = AIL5.invoice_id
                                    AND     AI5.state                   IN ('open', 'paid')
                                )                                                           AS invoice_date
                    ,           AIL4.product_id
                    ,           NULL                                                        AS presale_cost
                    ,           NULL                                                        AS presale_price
                    ,           NULL                                                        AS presale_price_variation
                    ,           NULL                                                        AS presale_margin
                    ,           NULL                                                        AS sale_cost
                    ,           NULL                                                        AS sale_price
                    ,           NULL                                                        AS sale_price_variation
                    ,           NULL                                                        AS sale_margin
                    ,           NULL                                                        AS delivered_cost
                    ,           AIL4.price_subtotal                                         AS invoiced_total
                    FROM        sale_order                                                  SO3
                    ,           account_invoice                                             AI4
                    ,           account_invoice_line                                        AIL4
                    WHERE       SO3.state                                                   IN ('sale', 'done', 'closed')
                    AND         AI4.origin                                                  = SO3.name
                    AND         AIL4.invoice_id                                             = AI4.id
                    AND         NOT EXISTS                                                  (   SELECT  *
                                                                                                FROM    sale_order_line_invoice_rel SOLIR4
                                                                                                WHERE   SOLIR4.invoice_line_id      = AIL4.id
                                                                                            )
            )""")

    @api.multi
    def _compute_presale_margin_perc(self):
        for rec in self:
            if rec.presale_price != 0:
                rec.presale_margin_perc = \
                    '%.2f' % (100.0 * (1.0 - rec.presale_cost / rec.presale_price))
            else:
                rec.presale_margin_perc = "N/E"

    @api.multi
    def _compute_sale_margin_perc(self):
        for rec in self:
            if rec.sale_price != 0:
                rec.sale_margin_perc = \
                    '%.2f' % (100.0 * (1.0 - rec.sale_cost / rec.sale_price))
            else:
                rec.sale_margin_perc = "N/E"

    @api.multi
    def _compute_ordered_real_margin(self):
        for rec in self:
            rec.ordered_real_margin = rec.sale_price - rec.delivered_cost

    @api.multi
    def _compute_ordered_real_margin_perc(self):
        for rec in self:
            if rec.sale_price != 0:
                rec.ordered_real_margin_perc = \
                    '%.2f' % (100.0 * (1.0 - rec.delivered_cost / rec.sale_price))
            else:
                rec.ordered_real_margin_perc = "N/E"

    @api.multi
    def _compute_invoiced_real_margin(self):
        for rec in self:
            rec.invoiced_real_margin = rec.invoiced_total - rec.delivered_cost

    @api.multi
    def _compute_invoiced_real_margin_perc(self):
        for rec in self:
            rec.invoiced_real_margin_perc = 100.0 * (1.0 - rec.delivered_cost / rec.invoiced_total)

    @api.multi
    def _compute_ordered_real_sale_margin_gap(self):
        for rec in self:
            rec.ordered_real_sale_margin_gap = rec.ordered_real_margin - rec.sale_margin

    @api.multi
    def _compute_ordered_real_sale_margin_gap_perc(self):
        for rec in self:
            if rec.ordered_real_margin != 0:
                rec.ordered_real_sale_margin_gap_perc = \
                    '%.2f' % (100.0 * rec.ordered_real_sale_margin_gap / rec.sale_margin)
            else:
                rec.ordered_real_sale_margin_gap_perc = "N/E"

    @api.multi
    def _compute_invoiced_real_sale_margin_gap(self):
        for rec in self:
            rec.invoiced_real_sale_margin_gap = rec.invoiced_real_margin - rec.sale_margin

    @api.multi
    def _compute_invoiced_real_sale_margin_gap_perc(self):
        for rec in self:
            if rec.invoiced_real_margin != 0:
                rec.invoiced_real_sale_margin_gap_perc = \
                    '%.2f' % (100.0 * rec.invoiced_real_sale_margin_gap / rec.sale_margin)
            else:
                rec.invoiced_real_sale_margin_gap_perc = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'presale_cost' not in fields:
            fields.append('presale_cost')
        if 'presale_price' not in fields:
            fields.append('presale_price')
        if 'sale_cost' not in fields:
            fields.append('sale_cost')
        if 'sale_price' not in fields:
            fields.append('sale_price')
        if 'delivered_cost' not in fields:
            fields.append('delivered_cost')
        if 'invoiced_total' not in fields:
            fields.append('invoiced_total')
        if 'sale_margin' not in fields:
            fields.append('sale_margin')
        if 'ordered_real_margin' not in fields:
            fields.append('ordered_real_margin')
        if 'ordered_real_sale_margin_gap' not in fields:
            fields.append('ordered_real_sale_margin_gap')
        if 'invoiced_real_margin' not in fields:
            fields.append('invoiced_real_margin')
        if 'invoiced_real_sale_margin_gap' not in fields:
            fields.append('invoiced_real_sale_margin_gap')
        res = super(OFSaleMarginRegulator, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'presale_margin_perc' in fields:
                if 'presale_cost' in line and line['presale_cost'] is not None and line.get('presale_price', False):
                    line['presale_margin_perc'] = \
                        ('%.2f' % (round(100.0 * (1.0 - line['presale_cost'] / line['presale_price']), 2))).\
                        replace('.', ',')
                else:
                    line['presale_margin_perc'] = "N/E"
            if 'sale_margin_perc' in fields:
                if 'sale_cost' in line and line['sale_cost'] is not None and line.get('sale_price', False):
                    line['sale_margin_perc'] = \
                        ('%.2f' % (round(100.0 * (1.0 - line['sale_cost'] / line['sale_price']), 2))).\
                        replace('.', ',')
                else:
                    line['sale_margin_perc'] = "N/E"
            if 'ordered_real_margin' in fields:
                if 'sale_price' in line and line['sale_price'] is not None and 'delivered_cost' in line and \
                        line['delivered_cost'] is not None:
                    line['ordered_real_margin'] = line['sale_price'] - line['delivered_cost']
            if 'ordered_real_margin_perc' in fields:
                if 'delivered_cost' in line and line['delivered_cost'] is not None and line.get('sale_price', False):
                    line['ordered_real_margin_perc'] = \
                        ('%.2f' % (round(100.0 * (1.0 - line['delivered_cost'] / line['sale_price']), 2))).\
                        replace('.', ',')
                else:
                    line['ordered_real_margin_perc'] = "N/E"
            if 'invoiced_real_margin' in fields:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                        'delivered_cost' in line and line['delivered_cost'] is not None:
                    line['invoiced_real_margin'] = line['invoiced_total'] - line['delivered_cost']
            if 'invoiced_real_margin_perc' in fields:
                if 'delivered_cost' in line and line['delivered_cost'] is not None and \
                        line.get('invoiced_total', False):
                    line['invoiced_real_margin_perc'] = \
                        ('%.2f' % (round(100.0 * (1.0 - line['delivered_cost'] / line['invoiced_total']), 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_real_margin_perc'] = "N/E"
            if 'ordered_real_sale_margin_gap' in fields:
                if 'sale_margin' in line and line['sale_margin'] is not None and 'ordered_real_margin' in line and \
                        line['ordered_real_margin'] is not None:
                    line['ordered_real_sale_margin_gap'] = line['ordered_real_margin'] - line['sale_margin']
            if 'ordered_real_sale_margin_gap_perc' in fields:
                if 'ordered_real_sale_margin_gap' in line and line['ordered_real_sale_margin_gap'] is not None and \
                        line.get('sale_margin', False):
                    line['ordered_real_sale_margin_gap_perc'] = \
                        ('%.2f' % (round(100.0 * line['ordered_real_sale_margin_gap'] / line['sale_margin'],
                                         2))).replace('.', ',')
                else:
                    line['ordered_real_sale_margin_gap_perc'] = "N/E"
            if 'invoiced_real_sale_margin_gap' in fields:
                if 'sale_margin' in line and line['sale_margin'] is not None and 'invoiced_real_margin' in line and \
                        line['invoiced_real_margin'] is not None:
                    line['invoiced_real_sale_margin_gap'] = line['invoiced_real_margin'] - line['sale_margin']
            if 'invoiced_real_sale_margin_gap_perc' in fields:
                if 'invoiced_real_sale_margin_gap' in line and line['invoiced_real_sale_margin_gap'] is not None and \
                        line.get('sale_margin', False):
                    line['invoiced_real_sale_margin_gap_perc'] = \
                        ('%.2f' % (round(100.0 * line['invoiced_real_sale_margin_gap'] / line['sale_margin'],
                                         2))).replace('.', ',')
                else:
                    line['invoiced_real_sale_margin_gap_perc'] = "N/E"

        return res
