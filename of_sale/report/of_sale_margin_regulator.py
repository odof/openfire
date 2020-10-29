# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools


class OFSaleMarginRegulator(models.Model):
    """Régule de marge"""

    _name = 'of.sale.margin.regulator'
    _auto = False
    _description = "Régule de marge"
    _rec_name = 'id'

    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u"Vendeur", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire", readonly=True)
    confirmation_date = fields.Date(string=u"Date de confirmation", readonly=True)
    invoice_date = fields.Date(string=u"Date de dernière facture", readonly=True)
    invoice_status = fields.Selection([
        ('upselling', u"Opportunité de montée en gamme"),
        ('invoiced', u"Entièrement facturé"),
        ('to invoice', u"À facturer"),
        ('no', u"Rien à facturer")
        ], string=u"État de facturation", readonly=True)
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", readonly=True)
    product_ref = fields.Char(string=u"Référence article", readonly=True)

    ordered_qty = fields.Float(string=u"Quantité commandée", readonly=True)
    ordered_cost = fields.Float(string=u"Coût commandé", readonly=True)
    ordered_total = fields.Float(string=u"Total HT commandé", readonly=True)
    ordered_margin = fields.Float(string=u"Marge sur commandé", readonly=True)
    delivered_qty = fields.Float(string=u"Quantité livrée", readonly=True)
    delivered_cost = fields.Float(string=u"Coût livré", readonly=True)
    delivered_total = fields.Float(string=u"Total HT livré", readonly=True)
    delivered_margin = fields.Float(string=u"Marge sur livré", readonly=True)
    invoiced_qty = fields.Float(string=u"Quantité facturée", readonly=True)
    invoiced_cost = fields.Float(string=u"Coût facturé", readonly=True)
    invoiced_total = fields.Float(string=u"Total HT facturé", readonly=True)
    invoiced_margin = fields.Float(string=u"Marge sur facturé", readonly=True)
    delivered_ordered_margin_gap = fields.Float(string=u"Écart de marge livré / commandé", readonly=True)
    delivered_ordered_margin_gap_perc = fields.Char(
        string=u"Écart de marge livré / commandé (%)", compute='_compute_delivered_ordered_margin_gap_perc',
        compute_sudo=True, readonly=True)
    invoiced_ordered_margin_gap = fields.Float(string=u"Écart de marge facturé / commandé", readonly=True)
    invoiced_ordered_margin_gap_perc = fields.Char(
        string=u"Écart de marge facturé / commandé (%)", compute='_compute_invoiced_ordered_margin_gap_perc',
        compute_sudo=True, readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_sale_margin_regulator')
        self._cr.execute("""
            CREATE VIEW of_sale_margin_regulator AS (
                    SELECT      SOL.id
                    ,           SO.company_id
                    ,           SO.user_id
                    ,           SO.partner_id
                    ,           SO.confirmation_date::timestamp::date           AS confirmation_date
                    ,           (   SELECT  MAX(AI.date_invoice)
                                    FROM    account_invoice                     AI
                                    ,       account_invoice_line                AIL
                                    ,       sale_order_line_invoice_rel         SOLIR
                                    WHERE   SOLIR.order_line_id                 = SOL.id
                                    AND     AIL.id                              = SOLIR.invoice_line_id
                                    AND     AI.id                               = AIL.invoice_id
                                    AND     AI.state                            IN ('open', 'paid')
                                )                                               AS invoice_date
                    ,           SOL.invoice_status
                    ,           SOL.order_id
                    ,           PP.default_code                                 AS product_ref
                    ,           SOL.product_uom_qty                             AS ordered_qty
                    ,           SOL.product_uom_qty * SOL.purchase_price        AS ordered_cost
                    ,           SOL.product_uom_qty * SOL.price_unit            AS ordered_total
                    ,           (SOL.product_uom_qty * SOL.price_unit)
                                -
                                (SOL.product_uom_qty * SOL.purchase_price)      AS ordered_margin
                    ,           SOL.qty_delivered                               AS delivered_qty
                    ,           SOL.qty_delivered * SOL.purchase_price          AS delivered_cost
                    ,           SOL.qty_delivered * SOL.price_unit              AS delivered_total
                    ,           (SOL.qty_delivered * SOL.price_unit)
                                -
                                (SOL.qty_delivered * SOL.purchase_price)        AS delivered_margin
                    ,           SOL.qty_invoiced                                AS invoiced_qty
                    ,           SOL.qty_invoiced * SOL.purchase_price           AS invoiced_cost
                    ,           SOL.qty_invoiced * SOL.price_unit               AS invoiced_total
                    ,           (SOL.qty_invoiced * SOL.price_unit)
                                -
                                (SOL.qty_invoiced * SOL.purchase_price)         AS invoiced_margin
                    ,           (   (SOL.qty_delivered * SOL.price_unit)
                                    -
                                    (SOL.qty_delivered * SOL.purchase_price)
                                )
                                -
                                (
                                    (SOL.product_uom_qty * SOL.price_unit)
                                    -
                                    (SOL.product_uom_qty * SOL.purchase_price)
                                )                                               AS delivered_ordered_margin_gap
                    ,           (   (SOL.qty_invoiced * SOL.price_unit)
                                    -
                                    (SOL.qty_invoiced * SOL.purchase_price)
                                )
                                -
                                (
                                    (SOL.product_uom_qty * SOL.price_unit)
                                    -
                                    (SOL.product_uom_qty * SOL.purchase_price)
                                )                                               AS invoiced_ordered_margin_gap
                    FROM        sale_order_line                                 SOL
                    ,           sale_order                                      SO
                    ,           product_product                                 PP
                    WHERE       SO.id                                           = SOL.order_id
                    AND         SO.state                                        = 'sale'
                    AND         PP.id                                           = SOL.product_id
            )""")

    @api.multi
    def _compute_delivered_ordered_margin_gap_perc(self):
        for rec in self:
            if rec.ordered_margin != 0:
                rec.delivered_ordered_margin_gap_perc = \
                    '%.2f' % (100.0 * rec.delivered_ordered_margin_gap / rec.ordered_margin)
            else:
                rec.delivered_ordered_margin_gap_perc = "N/E"

    @api.multi
    def _compute_invoiced_ordered_margin_gap_perc(self):
        for rec in self:
            if rec.ordered_margin != 0:
                rec.invoiced_ordered_margin_gap_perc = \
                    '%.2f' % (100.0 * rec.invoiced_ordered_margin_gap / rec.ordered_margin)
            else:
                rec.invoiced_ordered_margin_gap_perc = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'delivered_ordered_margin_gap' not in fields:
            fields.append('delivered_ordered_margin_gap')
        if 'ordered_margin' not in fields:
            fields.append('ordered_margin')
        if 'invoiced_ordered_margin_gap' not in fields:
            fields.append('invoiced_ordered_margin_gap')
        res = super(OFSaleMarginRegulator, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'delivered_ordered_margin_gap_perc' in fields:
                if line['ordered_margin'] != 0:
                    line['delivered_ordered_margin_gap_perc'] = \
                        ('%.2f' % (round(100.0 * line['delivered_ordered_margin_gap'] / line['ordered_margin'], 2))).\
                        replace('.', ',')
                else:
                    line['delivered_ordered_margin_gap_perc'] = "N/E"
            if 'invoiced_ordered_margin_gap_perc' in fields:
                if line['ordered_margin'] != 0:
                    line['invoiced_ordered_margin_gap_perc'] = \
                        ('%.2f' % (round(100.0 * line['invoiced_ordered_margin_gap'] / line['ordered_margin'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_ordered_margin_gap_perc'] = "N/E"

        return res
