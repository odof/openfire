# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import itertools
import math

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_total_eco_contribution = fields.Float(
        string=u"Dont éco-contribution PMCB", compute='_compute_of_total_eco_contribution')

    @api.depends('order_line.of_total_eco_contribution')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            record.of_total_eco_contribution = sum(record.mapped('order_line.of_total_eco_contribution'))

    @api.multi
    def recompute_eco_contribution(self):
        self_filtered = self.filtered(lambda r: r.state in ('draft', 'sent'))
        if not self_filtered:
            return
        lines = self_filtered.mapped('order_line')
        if not self.env['ir.values'].sudo().get_default(
                'account.config.settings', 'of_eco_contribution_price_included'):
            # Si l'éco contribution a été ajouté au prix unitaire de la ligne de commande,
            # on la soustrait avant de la recalculer
            lines._subtract_of_unit_eco_contribution()
        lines.mapped('kit_id.kit_line_ids')._compute_of_total_eco_contribution()
        lines._compute_of_total_eco_contribution()
        if not self.env['ir.values'].sudo().get_default(
                'account.config.settings', 'of_eco_contribution_price_included'):
            # Après avoir soustrait l'ancienne éco contribution, on ajoute la nouvelle
            lines._add_of_unit_eco_contribution()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)
    of_unit_eco_contribution = fields.Float(
        string=u"Montant unitaire éco-contribution", compute='_compute_of_total_eco_contribution', store=True)

    @api.onchange('product_id')
    def product_id_change(self):
        result = super(SaleOrderLine, self).product_id_change()
        if not self.env['ir.values'].sudo().get_default(
                'account.config.settings', 'of_eco_contribution_price_included'):
            # L'éco-contribution doit être incluse dans le prix unitaire
            self.price_unit = self.price_unit + self.of_unit_eco_contribution
        return result

    @api.depends(
        'product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'price_subtotal', 'of_total_eco_contribution'
    )
    def _product_margin(self):
        for line in self:
            currency = line.order_id.pricelist_id.currency_id
            price = line.purchase_price
            line.margin = currency.round(
                line.price_subtotal - line.of_total_eco_contribution - (price * line.product_uom_qty)
            )

    @api.depends('product_id', 'product_uom_qty', 'product_uom', 'kit_id.of_total_eco_contribution', 'of_is_kit',
                 'of_product_qty_brut')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            if record.of_is_kit:
                record.of_unit_eco_contribution = record.kit_id.of_total_eco_contribution
                record.of_total_eco_contribution = record.kit_id.of_total_eco_contribution * record.product_uom_qty
            elif record.product_id.of_eco_contribution_id:
                contribution = record.product_id.of_eco_contribution_id
                if record.product_id.of_packaging_unit and contribution.type in ['ton', 'unit']:
                    qty = int(math.ceil(round(record.product_uom_qty / record.product_id.of_packaging_unit, 3)))
                else:
                    original_uom = record.product_id.uom_id
                    current_uom = record.product_uom
                    qty = current_uom._compute_quantity(record.product_uom_qty, original_uom, round=False)
                if contribution.type == 'ton':
                    eco_contribution = contribution.price * record.product_id.weight / 1000.0
                else:
                    eco_contribution = contribution.price
                record.of_unit_eco_contribution = eco_contribution
                record.of_total_eco_contribution = qty * eco_contribution

    @api.multi
    def _add_of_unit_eco_contribution(self):
        for record in self.filtered(lambda r: r.of_unit_eco_contribution):
            record.price_unit = record.price_unit + record.of_unit_eco_contribution

    @api.multi
    def _subtract_of_unit_eco_contribution(self):
        for record in self.filtered(lambda r: r.of_unit_eco_contribution):
            record.price_unit = record.price_unit - record.of_unit_eco_contribution


class OfSaleOrderKit(models.Model):
    _inherit = 'of.saleorder.kit'

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)

    @api.depends('kit_line_ids.of_total_eco_contribution')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            record.of_total_eco_contribution = sum(record.mapped('kit_line_ids.of_total_eco_contribution'))

    @api.multi
    @api.depends('kit_line_ids', 'of_total_eco_contribution')
    def _compute_price_comps(self):
        add_eco = not self.env['ir.values'].sudo().get_default(
                'account.config.settings', 'of_eco_contribution_price_included')
        for kit in self:
            price = 0.0
            cost = 0.0
            if kit.kit_line_ids:
                for comp in kit.kit_line_ids:
                    price += comp.price_unit * comp.qty_per_kit
                    cost += comp.cost_unit * comp.qty_per_kit
                if add_eco:
                    price += kit.of_total_eco_contribution
                kit.price_comps = price
                kit.cost_comps = cost


class OfSaleOrderKitLine(models.Model):
    _inherit = 'of.saleorder.kit.line'

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)
    of_unit_eco_contribution = fields.Float(
        string=u"Montant unitaire éco-contribution", compute='_compute_of_total_eco_contribution', store=True)

    @api.depends('product_id', 'qty_per_kit', 'product_uom_id', 'kit_id.order_line_id.product_uom_qty')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            if record.product_id.of_eco_contribution_id:
                contribution = record.product_id.of_eco_contribution_id
                original_uom = record.product_id.uom_id
                current_uom = record.product_uom_id
                base_qty = record.qty_per_kit * record.kit_id.order_line_id.product_uom_qty
                qty = current_uom._compute_quantity(base_qty, original_uom, round=False)
                if contribution.type == 'ton':
                    eco_contribution = contribution.price * record.product_id.weight / 1000.0
                else:
                    eco_contribution = contribution.price
                record.of_unit_eco_contribution = eco_contribution
                record.of_total_eco_contribution = qty * eco_contribution
