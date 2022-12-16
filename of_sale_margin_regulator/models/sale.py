# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_margin_followup_ids = fields.One2many(
        comodel_name='of.sale.order.margin.followup', inverse_name='order_id', string=u"Suivi de la marge", copy=False)

    @api.multi
    def action_preconfirm(self):
        res = super(SaleOrder, self).action_preconfirm()

        # Stockage des infos de marge sur les lignes et calcul des totaux si elles n'existant pas déjà:
        if not self.of_margin_followup_ids.filtered(lambda rec: rec.type == 'presale'):
            total_presale_cost = 0.0
            total_presale_price = 0.0
            total_presale_price_variation = 0.0
            total_presale_margin = 0.0
            total_presale_margin_perc = 0.0
            for line in self.order_line:
                presale_cost = line.purchase_price * line.product_uom_qty
                presale_price = line.price_unit * line.product_uom_qty
                if line.of_is_kit and line.of_pricing == 'computed':
                    presale_price_variation = sum(line.kit_id.kit_line_ids.mapped(
                        lambda l: l.of_unit_price_variation * l.qty_total))
                else:
                    presale_price_variation = line.of_unit_price_variation * line.product_uom_qty
                presale_margin = line.margin
                if presale_price:
                    presale_margin_perc = 100.0 * (1.0 - presale_cost / presale_price)
                else:
                    presale_margin_perc = 0.0
                line.write({'of_presale_cost': presale_cost,
                            'of_presale_price': presale_price,
                            'of_presale_price_variation': presale_price_variation,
                            'of_presale_margin': presale_margin,
                            'of_presale_margin_perc': presale_margin_perc})
                total_presale_cost += presale_cost
                total_presale_price += presale_price
                total_presale_price_variation += presale_price_variation
                total_presale_margin += presale_margin
            if total_presale_price:
                total_presale_margin_perc = 100.0 * (1.0 - total_presale_cost / total_presale_price)

            # Création de la ligne de suivi de la marge (type Bon de commande)
            self.env['of.sale.order.margin.followup'].create(
                {'order_id': self.id,
                 'type': 'presale',
                 'date': fields.Datetime.now(),
                 'cost': total_presale_cost,
                 'price': total_presale_price,
                 'price_variation': total_presale_price_variation,
                 'margin': total_presale_margin,
                 'margin_perc': total_presale_margin_perc
                 })

        return res

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        # Stockage des infos de marge sur les lignes et calcul des totaux
        total_sale_cost = 0.0
        total_sale_price = 0.0
        total_sale_price_variation = 0.0
        total_sale_margin = 0.0
        total_sale_margin_perc = 0.0
        for line in self.order_line:
            sale_cost = line.purchase_price * line.product_uom_qty
            sale_price = line.price_unit * line.product_uom_qty
            if line.of_is_kit and line.of_pricing == 'computed':
                sale_price_variation = sum(line.kit_id.kit_line_ids.mapped(
                    lambda l: l.of_unit_price_variation * l.qty_total))
            else:
                sale_price_variation = line.of_unit_price_variation * line.product_uom_qty
            sale_margin = line.margin
            if sale_price:
                sale_margin_perc = 100.0 * (1.0 - sale_cost / sale_price)
            else:
                sale_margin_perc = 0.0
            line.write({'of_sale_cost': sale_cost,
                        'of_sale_price': sale_price,
                        'of_sale_price_variation': sale_price_variation,
                        'of_sale_margin': sale_margin,
                        'of_sale_margin_perc': sale_margin_perc})
            total_sale_cost += sale_cost
            total_sale_price += sale_price
            total_sale_price_variation += sale_price_variation
            total_sale_margin += sale_margin
        if total_sale_price:
            total_sale_margin_perc = 100.0 * (1.0 - total_sale_cost / total_sale_price)

        # Création de la ligne de suivi de la marge (type Commande enregistrée)
        self.env['of.sale.order.margin.followup'].create(
            {'order_id': self.id,
             'type': 'sale',
             'date': fields.Datetime.now(),
             'cost': total_sale_cost,
             'price': total_sale_price,
             'price_variation': total_sale_price_variation,
             'margin': total_sale_margin,
             'margin_perc': total_sale_margin_perc
             })

        return res

    @api.multi
    def action_cancel(self):
        self.mapped('of_margin_followup_ids').filtered(lambda rec: rec.type == 'sale').\
            write({'cancelled': True})
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def button_commercial_cancellation(self):
        self.ensure_one()

        if self.state != 'sale':
            raise UserError(u"Seules les commandes validées peuvent être annulées commercialement !")

        # Création d'une commande inverse
        cancel_order = self.copy(default={'of_cancelled_order_id': self.id,
                                          'origin': self.name,
                                          'client_order_ref': self.client_order_ref,
                                          'opportunity_id': self.opportunity_id.id,
                                          'project_id': self.project_id.id,
                                          'campaign_id': self.campaign_id.id,
                                          'medium_id': self.medium_id.id,
                                          'source_id': self.source_id.id,
                                          'of_referred_id': self.of_referred_id.id})
        cancel_order.order_line.mapped(lambda line: line.write({'product_uom_qty': -line.product_uom_qty}))
        cancel_order.with_context(order_cancellation=True).action_preconfirm()
        cancel_order.with_context(order_cancellation=True).action_confirm()

        # Annulation des objets liés à la commande d'origine

        # Annulation BLs
        self.picking_ids.filtered(lambda p: not any(move.state == 'done' for move in p.move_lines)).action_cancel()

        # Annulation factures brouillons
        self.invoice_ids.filtered(lambda i: i.state == 'draft').action_invoice_cancel()

        # Annulation demandes de prix
        self.env['purchase.order'].search([('sale_order_id', '=', self.id), ('state', '=', 'draft')]).button_cancel()

        self.of_commercially_cancelled = True
        self.of_cancellation_order_id = cancel_order.id
        # On bloque la commande annulée ainsi que la commande d'annulation
        self.action_done()
        cancel_order.action_done()

        action = self.env.ref('sale.action_orders').read()[0]
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['res_id'] = cancel_order.id

        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_presale_cost = fields.Float(string=u"Prix de revient à la confirmation")
    of_presale_price = fields.Float(string=u"Prix de vente à la confirmation")
    of_presale_price_variation = fields.Float(string=u"Variation de prix à la confirmation")
    of_presale_margin = fields.Float(string=u"Marge à la confirmation (€)")
    of_presale_margin_perc = fields.Float(string=u"Marge à la confirmation (%)")

    of_sale_cost = fields.Float(string=u"Prix de revient à l'enregistrement")
    of_sale_price = fields.Float(string=u"Prix de vente à l'enregistrement")
    of_sale_price_variation = fields.Float(string=u"Variation de prix à l'enregistrement")
    of_sale_margin = fields.Float(string=u"Marge à l'enregistrement (€)")
    of_sale_margin_perc = fields.Float(string=u"Marge à l'enregistrement (%)")

    @api.model_cr_context
    def _auto_init(self):
        # On initialise les valeurs "à l'enregistrement" pour les commandes déjà enregistrées
        cr = self._cr
        cr.execute(
            """ SELECT  *
                FROM    information_schema.columns
                WHERE   table_name                  = '%s'
                AND     column_name                 = 'of_presale_cost'
            """ % self._table)
        exists = bool(cr.fetchall())
        res = super(SaleOrderLine, self)._auto_init()
        if not exists:
            cr.execute(
                """ UPDATE  sale_order_line     SOL
                    SET     of_sale_cost        = SOL.purchase_price * SOL.product_uom_qty
                    ,       of_sale_price       = SOL.price_unit * SOL.product_uom_qty
                    ,       of_sale_margin      = SOL.margin
                    ,       of_sale_margin_perc =   CASE
                                                        WHEN SOL.price_unit * SOL.product_uom_qty != 0 THEN
                                                            100.0 * (1.0 - SOL.purchase_price / SOL.price_unit)
                                                        ELSE
                                                            0.0
                                                    END
                    FROM    sale_order          SO
                    WHERE   SO.state            IN ('sale', 'done', 'closed')
                    AND     SOL.order_id        = SO.id
                """)
        return res


class OFSaleOrderMarginFollowup(models.Model):
    _name = 'of.sale.order.margin.followup'
    _description = u"Suivi de marge pour les commandes de vente"
    _order = 'type, date desc, id desc'

    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", ondelete='cascade')
    type = fields.Selection(
        selection=[('presale', u"Marge Bon de commande"),
                   ('sale', u"Marge Commande enregistrée")], string=u"Scénario de marge")
    date = fields.Datetime(string=u"Date")
    cancelled = fields.Boolean(string=u"Annulé")
    cost = fields.Float(string=u"Prix de revient")
    price = fields.Float(string=u"Prix de vente")
    price_variation = fields.Float(string=u"Variation de prix")
    margin = fields.Float(string=u"Marge (€)")
    margin_perc = fields.Float(string=u"Marge (%)")

    @api.model_cr_context
    def _auto_init(self):
        init = False
        cr = self._cr
        cr.execute("""
            SELECT  1
            FROM    of_sale_order_margin_followup
            WHERE   type                            = 'confirmation'
        """)
        if cr.fetchall():
            init = True

        res = super(OFSaleOrderMarginFollowup, self)._auto_init()

        if init:
            # On crée le scénario "Confirmation" pour les commandes déjà validées
            cr = self._cr
            cr.execute("DELETE FROM of_sale_order_margin_followup")
            cr.execute(
                """ INSERT INTO of_sale_order_margin_followup
                    (   create_uid
                    ,   create_date
                    ,   write_uid
                    ,   write_date
                    ,   order_id
                    ,   type
                    ,   date
                    ,   cost
                    ,   price
                    ,   margin
                    ,   margin_perc
                    )
                    (   SELECT  1
                        ,       NOW()
                        ,       1
                        ,       NOW()
                        ,       SO.id
                        ,       'sale'
                        ,       NOW()
                        ,       SUM(SOL.of_sale_cost)
                        ,       SUM(SOL.of_sale_price)
                        ,       SUM(SOL.of_sale_margin)
                        ,       CASE
                                    WHEN SUM(SOL.of_sale_price) != 0 THEN
                                        100.0 * (1.0 - SUM(SOL.of_sale_cost) / SUM(SOL.of_sale_price))
                                    ELSE
                                        0.0
                                END
                        FROM    sale_order          SO
                        ,       sale_order_line     SOL
                        WHERE   SO.state            IN ('sale', 'done', 'closed')
                        AND     SOL.order_id        = SO.id
                        GROUP BY SO.id
                    )
                """)

        return res
