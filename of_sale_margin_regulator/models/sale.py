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

        # Stockage des infos de marge sur les lignes et calcul des totaux
        total_sale_cost = 0.0
        total_sale_price = 0.0
        total_sale_discount = 0.0
        total_sale_margin = 0.0
        total_sale_margin_perc = 0.0
        for line in self.order_line:
            sale_cost = line.purchase_price * line.product_uom_qty
            sale_price = line.price_unit * line.product_uom_qty
            sale_discount = line.of_unit_discount_amount * line.product_uom_qty
            sale_margin = line.margin
            if sale_price:
                sale_margin_perc = 100.0 * (1.0 - sale_cost / sale_price)
            else:
                sale_margin_perc = 0.0
            line.write({'of_sale_cost': sale_cost,
                        'of_sale_price': sale_price,
                        'of_sale_discount': sale_discount,
                        'of_sale_margin': sale_margin,
                        'of_sale_margin_perc': sale_margin_perc})
            total_sale_cost += sale_cost
            total_sale_price += sale_price
            total_sale_discount += sale_discount
            total_sale_margin += sale_margin
        if total_sale_price:
            total_sale_margin_perc = 100.0 * (1.0 - total_sale_cost / total_sale_price)

        # Création de la ligne de suivi de la marge (type Vente)
        self.env['of.sale.order.margin.followup'].create(
            {'order_id': self.id,
             'type': 'sale',
             'cost': total_sale_cost,
             'price': total_sale_price,
             'discount': total_sale_discount,
             'margin': total_sale_margin,
             'margin_perc': total_sale_margin_perc
             })

        return True

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()

        # Stockage des infos de marge sur les lignes et calcul des totaux
        total_validation_cost = 0.0
        total_validation_price = 0.0
        total_validation_discount = 0.0
        total_validation_margin = 0.0
        total_validation_margin_perc = 0.0
        for line in self.order_line:
            validation_cost = line.purchase_price * line.product_uom_qty
            validation_price = line.price_unit * line.product_uom_qty
            validation_discount = line.of_unit_discount_amount * line.product_uom_qty
            validation_margin = line.margin
            if validation_price:
                validation_margin_perc = 100.0 * (1.0 - validation_cost / validation_price)
            else:
                validation_margin_perc = 0.0
            line.write({'of_validation_cost': validation_cost,
                        'of_validation_price': validation_price,
                        'of_validation_discount': validation_discount,
                        'of_validation_margin': validation_margin,
                        'of_validation_margin_perc': validation_margin_perc})
            total_validation_cost += validation_cost
            total_validation_price += validation_price
            total_validation_discount += validation_discount
            total_validation_margin += validation_margin
        if total_validation_price:
            total_validation_margin_perc = 100.0 * (1.0 - total_validation_cost / total_validation_price)

        # Création de la ligne de suivi de la marge (type Vente)
        self.env['of.sale.order.margin.followup'].create(
            {'order_id': self.id,
             'type': 'validation',
             'cost': total_validation_cost,
             'price': total_validation_price,
             'discount': total_validation_discount,
             'margin': total_validation_margin,
             'margin_perc': total_validation_margin_perc
             })

        return True

    @api.multi
    def action_reopen(self):
        self.ensure_one()
        self.state = 'sale'
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_sale_cost = fields.Float(string=u"Prix de revient sur vente")
    of_sale_price = fields.Float(string=u"Prix de vente sur vente")
    of_sale_discount = fields.Float(string=u"Remise sur vente")
    of_sale_margin = fields.Float(string=u"Marge sur vente (€)")
    of_sale_margin_perc = fields.Float(string=u"Marge sur vente (%)")

    of_validation_cost = fields.Float(string=u"Prix de revient sur validation")
    of_validation_price = fields.Float(string=u"Prix de vente sur validation")
    of_validation_discount = fields.Float(string=u"Remise sur validation")
    of_validation_margin = fields.Float(string=u"Marge sur validation (€)")
    of_validation_margin_perc = fields.Float(string=u"Marge sur validation (%)")


class OFSaleOrderMarginFollowup(models.Model):
    _name = 'of.sale.order.margin.followup'
    _description = u"Suivi de marge pour les commandes de vente"

    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", ondelete='cascade')
    type = fields.Selection(
        selection=[('sale', u"Vente"), ('validation', u"Validation")], string=u"Scénario de marge")
    cost = fields.Float(string=u"Prix de revient")
    price = fields.Float(string=u"Prix de vente")
    discount = fields.Float(string=u"Remise")
    margin = fields.Float(string=u"Marge (€)")
    margin_perc = fields.Float(string=u"Marge (%)")
