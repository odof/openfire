# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_validated = fields.Boolean(string=u"Devis validé", copy=False)
    of_margin_followup_ids = fields.One2many(
        comodel_name='of.sale.order.margin.followup', inverse_name='order_id', string=u"Suivi de la marge", copy=False)
    state = fields.Selection(selection_add=[('closed', u"Clôturé")])

    @api.multi
    def action_validate(self):
        self.ensure_one()

        self.of_validated = True

        # Création du suivi de commande
        self.with_context(auto_followup=True, followup_creator_id=self.env.user.id).sudo().action_followup_project()

        # Stockage des infos de marge sur les lignes et calcul des totaux si elles n'existant pas déjà:
        if not self.of_margin_followup_ids.filtered(lambda rec: rec.type == 'sale'):
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

            # Création de la ligne de suivi de la marge (type Vente)
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

        return True

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()

        # Stockage des infos de marge sur les lignes et calcul des totaux
        total_confirmation_cost = 0.0
        total_confirmation_price = 0.0
        total_confirmation_price_variation = 0.0
        total_confirmation_margin = 0.0
        total_confirmation_margin_perc = 0.0
        for line in self.order_line:
            confirmation_cost = line.purchase_price * line.product_uom_qty
            confirmation_price = line.price_unit * line.product_uom_qty
            if line.of_is_kit and line.of_pricing == 'computed':
                confirmation_price_variation = sum(line.kit_id.kit_line_ids.mapped(
                    lambda l: l.of_unit_price_variation * l.qty_total))
            else:
                confirmation_price_variation = line.of_unit_price_variation * line.product_uom_qty
            confirmation_margin = line.margin
            if confirmation_price:
                confirmation_margin_perc = 100.0 * (1.0 - confirmation_cost / confirmation_price)
            else:
                confirmation_margin_perc = 0.0
            line.write({'of_confirmation_cost': confirmation_cost,
                        'of_confirmation_price': confirmation_price,
                        'of_confirmation_price_variation': confirmation_price_variation,
                        'of_confirmation_margin': confirmation_margin,
                        'of_confirmation_margin_perc': confirmation_margin_perc})
            total_confirmation_cost += confirmation_cost
            total_confirmation_price += confirmation_price
            total_confirmation_price_variation += confirmation_price_variation
            total_confirmation_margin += confirmation_margin
        if total_confirmation_price:
            total_confirmation_margin_perc = 100.0 * (1.0 - total_confirmation_cost / total_confirmation_price)

        # Création de la ligne de suivi de la marge (type Vente)
        self.env['of.sale.order.margin.followup'].create(
            {'order_id': self.id,
             'type': 'confirmation',
             'date': fields.Datetime.now(),
             'cost': total_confirmation_cost,
             'price': total_confirmation_price,
             'price_variation': total_confirmation_price_variation,
             'margin': total_confirmation_margin,
             'margin_perc': total_confirmation_margin_perc
             })

        return True

    @api.multi
    def action_cancel(self):
        self.write({'of_validated': False})
        self.mapped('of_margin_followup_ids').filtered(lambda rec: rec.type == 'confirmation').\
            write({'cancelled': True})
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def action_reopen(self):
        self.ensure_one()
        # On ré-ouvre le suivi
        if self.of_followup_project_id:
            self.of_followup_project_id.set_to_in_progress()
        self.state = 'sale'
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_sale_cost = fields.Float(string=u"Prix de revient sur vente")
    of_sale_price = fields.Float(string=u"Prix de vente sur vente")
    of_sale_price_variation = fields.Float(string=u"Variation de prix sur vente")
    of_sale_margin = fields.Float(string=u"Marge sur vente (€)")
    of_sale_margin_perc = fields.Float(string=u"Marge sur vente (%)")

    of_confirmation_cost = fields.Float(string=u"Prix de revient sur confirmation")
    of_confirmation_price = fields.Float(string=u"Prix de vente sur confirmation")
    of_confirmation_price_variation = fields.Float(string=u"Variation de prix sur confirmation")
    of_confirmation_margin = fields.Float(string=u"Marge sur confirmation (€)")
    of_confirmation_margin_perc = fields.Float(string=u"Marge sur confirmation (%)")

    @api.model_cr_context
    def _auto_init(self):
        # On initialise les valeurs "sur confirmation" pour les commandes déjà validées
        cr = self._cr
        cr.execute(
            """ SELECT  *
                FROM    information_schema.columns
                WHERE   table_name                  = '%s'
                AND     column_name                 = 'of_confirmation_cost'
            """ % self._table)
        exists = bool(cr.fetchall())
        res = super(SaleOrderLine, self)._auto_init()
        if not exists:
            cr.execute(
                """ UPDATE  sale_order_line         SOL
                    SET of_confirmation_cost        = SOL.purchase_price * SOL.product_uom_qty
                    ,   of_confirmation_price       = SOL.price_unit * SOL.product_uom_qty
                    ,   of_confirmation_margin      = SOL.margin
                    ,   of_confirmation_margin_perc =   CASE
                                                            WHEN SOL.price_unit * SOL.product_uom_qty != 0 THEN
                                                                100.0 * (1.0 - SOL.purchase_price / SOL.price_unit)
                                                            ELSE
                                                                0.0
                                                        END
                    FROM    sale_order              SO
                    WHERE   SO.state                IN ('sale', 'done', 'closed')
                    AND     SOL.order_id            = SO.id
                """)
        return res


class OFSaleOrderMarginFollowup(models.Model):
    _name = 'of.sale.order.margin.followup'
    _description = u"Suivi de marge pour les commandes de vente"
    _order = 'type desc, date desc, id desc'

    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", ondelete='cascade')
    type = fields.Selection(
        selection=[('sale', u"Vente"), ('confirmation', u"Confirmation")], string=u"Scénario de marge")
    date = fields.Datetime(string=u"Date")
    cancelled = fields.Boolean(string=u"Annulé")
    cost = fields.Float(string=u"Prix de revient")
    price = fields.Float(string=u"Prix de vente")
    price_variation = fields.Float(string=u"Variation de prix")
    margin = fields.Float(string=u"Marge (€)")
    margin_perc = fields.Float(string=u"Marge (%)")

    @api.model_cr_context
    def _auto_init(self):
        # On crée le scénario "Confirmation" pour les commandes déjà validées
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % (self._table,))
        exists = bool(cr.fetchall())
        res = super(OFSaleOrderMarginFollowup, self)._auto_init()
        if not exists:
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
                        ,       'confirmation'
                        ,       NOW()
                        ,       SUM(SOL.of_confirmation_cost)
                        ,       SUM(SOL.of_confirmation_price)
                        ,       SUM(SOL.of_confirmation_margin)
                        ,       CASE
                                    WHEN SUM(SOL.of_confirmation_price) != 0 THEN
                                        100.0 * (1.0 - SUM(SOL.of_confirmation_cost) / SUM(SOL.of_confirmation_price))
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
