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
    confirmation_date = fields.Date(string=u"Date de confirmation", readonly=True)
    invoice_date = fields.Date(string=u"Date de dernière facture", readonly=True)
    invoice_status = fields.Selection([
        ('upselling', u"Opportunité de montée en gamme"),
        ('invoiced', u"Entièrement facturé"),
        ('to invoice', u"À facturer"),
        ('no', u"Rien à facturer")
        ], string=u"État de facturation", readonly=True)
    ordered_cost = fields.Float(string=u"Coût commandé", readonly=True)
    ordered_total = fields.Float(string=u"Total HT commandé", readonly=True)
    ordered_margin = fields.Float(
        string=u"Marge sur commandé", compute='_compute_ordered_margin', compute_sudo=True, readonly=True)
    delivered_cost = fields.Float(string=u"Coût livré", readonly=True)
    delivered_margin = fields.Float(
        string=u"Marge sur livré", compute='_compute_delivered_margin', compute_sudo=True, readonly=True)
    invoiced_cost = fields.Float(string=u"Coût facturé", readonly=True)
    invoiced_total = fields.Float(string=u"Total HT facturé", readonly=True)
    invoiced_margin = fields.Float(
        string=u"Marge sur facturé", compute='_compute_invoiced_margin', compute_sudo=True, readonly=True)
    delivered_ordered_margin_gap = fields.Float(
        string=u"Écart de marge livré / commandé", compute='_compute_delivered_ordered_margin_gap', compute_sudo=True,
        readonly=True)
    delivered_ordered_margin_gap_perc = fields.Char(
        string=u"Écart de marge livré / commandé (%)", compute='_compute_delivered_ordered_margin_gap_perc',
        compute_sudo=True, readonly=True)
    invoiced_ordered_margin_gap = fields.Float(
        string=u"Écart de marge facturé / commandé", compute='_compute_invoiced_ordered_margin_gap', compute_sudo=True,
        readonly=True)
    invoiced_ordered_margin_gap_perc = fields.Char(
        string=u"Écart de marge facturé / commandé (%)", compute='_compute_invoiced_ordered_margin_gap_perc',
        compute_sudo=True, readonly=True)
    ordered_delivered_margin_regulator = fields.Float(
        string=u"Régule de marge commandé / livré", compute='_compute_ordered_delivered_margin_regulator',
        compute_sudo=True, readonly=True)
    ordered_delivered_margin_regulator_perc = fields.Char(
        string=u"Régule de marge commandé / livré (%)", compute='_compute_ordered_delivered_margin_regulator_perc',
        compute_sudo=True, readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_sale_margin_regulator')
        self._cr.execute("""
            CREATE VIEW of_sale_margin_regulator AS (
                    SELECT      SO.id
                    ,           SO.id                                                       AS order_id
                    ,           SO.company_id
                    ,           SO.user_id
                    ,           SO.partner_id
                    ,           SO.confirmation_date::timestamp::date                       AS confirmation_date
                    ,           (   SELECT  MAX(AI.date_invoice)
                                    FROM    sale_order_line                                 SOL
                                    ,       sale_order_line_invoice_rel                     SOLIR
                                    ,       account_invoice_line                            AIL
                                    ,       account_invoice                                 AI
                                    WHERE   SOL.order_id                                    = SO.id
                                    AND     SOLIR.order_line_id                             = SOL.id
                                    AND     AIL.id                                          = SOLIR.invoice_line_id
                                    AND     AI.id                                           = AIL.invoice_id
                                    AND     AI.state                                        IN ('open', 'paid')
                                )                                                           AS invoice_date
                    ,           SO.invoice_status
                    ,           SO.amount_untaxed                                           AS ordered_total
                    ,           (   SELECT  SUM(SOL.purchase_price * SOL.product_uom_qty)
                                    FROM    sale_order_line                                 SOL
                                    WHERE   SOL.order_id                                    = SO.id
                                )                                                           AS ordered_cost
                    ,           (   SELECT  SUM(SM.of_unit_cost)
                                    FROM    stock_picking                                   SP
                                    ,       stock_move                                      SM
                                    WHERE   SP.group_id                                     = SO.procurement_group_id
                                    AND     SM.picking_id                                   = SP.id
                                    AND     SM.state                                        = 'done'
                                )                                                           AS delivered_cost
                    ,           (   SELECT  SUM(AIL2.price_subtotal)
                                    FROM    (   SELECT DISTINCT
                                                        AI.id
                                                FROM    sale_order_line                     SOL
                                                ,       sale_order_line_invoice_rel         SOLIR
                                                ,       account_invoice_line                AIL
                                                ,       account_invoice                     AI
                                                WHERE   SOL.order_id                        = SO.id
                                                AND     SOLIR.order_line_id                 = SOL.id
                                                AND     AIL.id                              = SOLIR.invoice_line_id
                                                AND     AI.id                               = AIL.invoice_id
                                                AND     AI.state                            IN ('open', 'paid')
                                            )                                               TMP
                                    ,       account_invoice_line                            AIL2
                                    WHERE   AIL2.invoice_id                                 = TMP.id
                                )                                                           AS invoiced_total
                    ,           (   SELECT  SUM(AIL2.of_unit_cost * AIL2.quantity)
                                    FROM    (   SELECT DISTINCT
                                                        AI.id
                                                FROM    sale_order_line                     SOL
                                                ,       sale_order_line_invoice_rel         SOLIR
                                                ,       account_invoice_line                AIL
                                                ,       account_invoice                     AI
                                                WHERE   SOL.order_id                        = SO.id
                                                AND     SOLIR.order_line_id                 = SOL.id
                                                AND     AIL.id                              = SOLIR.invoice_line_id
                                                AND     AI.id                               = AIL.invoice_id
                                                AND     AI.state                            IN ('open', 'paid')
                                            )                                               TMP
                                    ,       account_invoice_line                            AIL2
                                    WHERE   AIL2.invoice_id                                 = TMP.id
                                )                                                           AS invoiced_cost
                    FROM        sale_order                                                  SO
                    WHERE       SO.state                                                    = 'sale'
            )""")

    @api.multi
    def _compute_ordered_margin(self):
        for rec in self:
            rec.ordered_margin = rec.ordered_total - rec.ordered_cost

    @api.multi
    def _compute_delivered_cost(self):
        for rec in self:
            delivered_cost = 0.0
            for move in rec.order_id.picking_ids.mapped('move_lines').filtered(lambda m: m.state == 'done'):
                purchase_procurement_orders = self.env['procurement.order'].search([('move_dest_id', '=', move.id)])
                validated_purchase_lines = purchase_procurement_orders.mapped('purchase_line_id').filtered(
                    lambda l: l.order_id.state == 'purchase')
                if validated_purchase_lines:
                    purchase_prices = validated_purchase_lines.mapped('price_unit')
                    unit_cost = sum(purchase_prices)/len(purchase_prices)
                    unit_cost = round(unit_cost * move.product_id.property_of_purchase_coeff)
                elif move.procurement_id.sale_line_id:
                    unit_cost = move.procurement_id.sale_line_id.purchase_price
                else:
                    unit_cost = move.product_id.standard_price
                delivered_cost += unit_cost * move.product_uom_qty
            rec.delivered_cost = delivered_cost

    @api.multi
    def _compute_delivered_margin(self):
        for rec in self:
            rec.delivered_margin = rec.ordered_total - rec.delivered_cost

    @api.multi
    def _compute_invoiced_margin(self):
        for rec in self:
            rec.invoiced_margin = rec.invoiced_total - rec.invoiced_cost

    @api.multi
    def _compute_delivered_ordered_margin_gap(self):
        for rec in self:
            rec.delivered_ordered_margin_gap = rec.delivered_margin - rec.ordered_margin

    @api.multi
    def _compute_delivered_ordered_margin_gap_perc(self):
        for rec in self:
            if rec.ordered_margin != 0:
                rec.delivered_ordered_margin_gap_perc = \
                    '%.2f' % (100.0 * rec.delivered_ordered_margin_gap / rec.ordered_margin)
            else:
                rec.delivered_ordered_margin_gap_perc = "N/E"

    @api.multi
    def _compute_invoiced_ordered_margin_gap(self):
        for rec in self:
            rec.invoiced_ordered_margin_gap = rec.invoiced_margin - rec.ordered_margin

    @api.multi
    def _compute_invoiced_ordered_margin_gap_perc(self):
        for rec in self:
            if rec.ordered_margin != 0:
                rec.invoiced_ordered_margin_gap_perc = \
                    '%.2f' % (100.0 * rec.invoiced_ordered_margin_gap / rec.ordered_margin)
            else:
                rec.invoiced_ordered_margin_gap_perc = "N/E"

    @api.multi
    def _compute_ordered_delivered_margin_regulator(self):
        # Coût commandé - coût livré
        for rec in self:
            rec.ordered_delivered_margin_regulator = rec.ordered_cost - rec.delivered_cost

    @api.multi
    def _compute_ordered_delivered_margin_regulator_perc(self):
        for rec in self:
            if rec.ordered_total != 0:
                rec.ordered_delivered_margin_regulator_perc = \
                    '%.2f' % (100.0 * rec.ordered_delivered_margin_regulator / rec.ordered_total)
            else:
                rec.ordered_delivered_margin_regulator_perc = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'ordered_total' not in fields:
            fields.append('ordered_total')
        if 'ordered_cost' not in fields:
            fields.append('ordered_cost')
        if 'ordered_margin' not in fields:
            fields.append('ordered_margin')
        if 'delivered_cost' not in fields:
            fields.append('delivered_cost')
        if 'delivered_margin' not in fields:
            fields.append('delivered_margin')
        if 'invoiced_total' not in fields:
            fields.append('invoiced_total')
        if 'invoiced_cost' not in fields:
            fields.append('invoiced_cost')
        if 'invoiced_margin' not in fields:
            fields.append('invoiced_margin')
        if 'delivered_ordered_margin_gap' not in fields:
            fields.append('delivered_ordered_margin_gap')
        if 'invoiced_ordered_margin_gap' not in fields:
            fields.append('invoiced_ordered_margin_gap')
        if 'ordered_delivered_margin_regulator' not in fields:
            fields.append('ordered_delivered_margin_regulator')
        res = super(OFSaleMarginRegulator, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'ordered_margin' in fields:
                if 'ordered_total' in line and line['ordered_total'] is not None and \
                   'ordered_cost' in line and line['ordered_cost'] is not None:
                    line['ordered_margin'] = line['ordered_total'] - line['ordered_cost']
            if 'delivered_margin' in fields:
                if 'ordered_total' in line and line['ordered_total'] is not None and \
                   'delivered_cost' in line and line['delivered_cost'] is not None:
                    line['delivered_margin'] = line['ordered_total'] - line['delivered_cost']
            if 'invoiced_margin' in fields:
                if 'invoiced_total' in line and line['invoiced_total'] is not None and \
                   'invoiced_cost' in line and line['invoiced_cost'] is not None:
                    line['invoiced_margin'] = line['invoiced_total'] - line['invoiced_cost']
            if 'delivered_ordered_margin_gap' in fields:
                if 'delivered_margin' in line and line['delivered_margin'] is not None and \
                   'ordered_margin' in line and line['ordered_margin'] is not None:
                    line['delivered_ordered_margin_gap'] = line['delivered_margin'] - line['ordered_margin']
            if 'delivered_ordered_margin_gap_perc' in fields:
                if 'delivered_ordered_margin_gap' in line and line['delivered_ordered_margin_gap'] is not None and \
                   'ordered_margin' in line and line['ordered_margin'] is not None and line['ordered_margin']:
                    line['delivered_ordered_margin_gap_perc'] = \
                        ('%.2f' % (round(100.0 * line['delivered_ordered_margin_gap'] / line['ordered_margin'], 2))).\
                        replace('.', ',')
                else:
                    line['delivered_ordered_margin_gap_perc'] = "N/E"
            if 'invoiced_ordered_margin_gap' in fields:
                if 'invoiced_margin' in line and line['invoiced_margin'] is not None and \
                   'ordered_margin' in line and line['ordered_margin'] is not None:
                    line['invoiced_ordered_margin_gap'] = line['invoiced_margin'] - line['ordered_margin']
            if 'invoiced_ordered_margin_gap_perc' in fields:
                if 'invoiced_ordered_margin_gap' in line and line['invoiced_ordered_margin_gap'] is not None and \
                   'ordered_margin' in line and line['ordered_margin'] is not None and line['ordered_margin']:
                    line['invoiced_ordered_margin_gap_perc'] = \
                        ('%.2f' % (round(100.0 * line['invoiced_ordered_margin_gap'] / line['ordered_margin'], 2))).\
                        replace('.', ',')
                else:
                    line['invoiced_ordered_margin_gap_perc'] = "N/E"
            if 'ordered_delivered_margin_regulator' in fields:
                if 'ordered_cost' in line and line['ordered_cost'] is not None and \
                   'delivered_cost' in line and line['delivered_cost'] is not None:
                    line['ordered_delivered_margin_regulator'] = line['ordered_cost'] - line['delivered_cost']
            if 'ordered_delivered_margin_regulator_perc' in fields:
                if 'ordered_delivered_margin_regulator' in line and \
                        line['ordered_delivered_margin_regulator'] is not None and \
                   'ordered_total' in line and line['ordered_total'] is not None and line['ordered_total']:
                    line['ordered_delivered_margin_regulator_perc'] = \
                        ('%.2f' %
                         (round(100.0 * line['ordered_delivered_margin_regulator'] / line['ordered_total'], 2))).\
                        replace('.', ',')
                else:
                    line['ordered_delivered_margin_regulator_perc'] = "N/E"

        return res
