# -*- coding: utf-8 -*-

from odoo import api, models


class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    @api.multi
    def _appliquer(self, values):
        super(GestionPrix, self)._appliquer(values)
        self.order_id.order_line.with_context(clear_cache='of_gestion_prix')._refresh_price_unit()


class GestionPrixLine(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix.line'

    @api.multi
    def get_sorted(self):
        return self.sorted(
            key=lambda line:
                line.quantity * (
                    min(line.order_line_id.kit_id.kit_line_ids.filtered('price_unit').mapped('qty_per_kit'))
                    if line.order_line_id.of_is_kit and line.order_line_id.of_pricing == 'computed'
                    else 1),
            reverse=True)

    def get_distributed_amount(self, to_distribute, total, currency, cost_prorata, rounding, line_rounding,
                               kit_lines_price_unit=False):
        self.ensure_one()
        order_line = self.order_line_id
        if order_line.of_is_kit and order_line.of_pricing == 'computed':
            # Le calcul du prix doit se faire sur les composants

            kit_lines = order_line.kit_id.kit_line_ids.sorted('qty_per_kit', reverse=True)
            if cost_prorata:
                to_distribute = total and order_line.purchase_price * to_distribute / total
            else:
                to_distribute = total and order_line.price_unit * to_distribute / total

            if kit_lines_price_unit:
                total = sum(
                    kit_lines_price_unit[kit_line]['price_unit'] * kit_line.qty_per_kit
                    for kit_line in kit_lines)
            else:
                # Calcul des prix pour éviter l'arrondi du montant si on appelait order_line.price_unit
                total = sum(kit_line.price_unit * kit_line.qty_per_kit for kit_line in kit_lines)

            values = {}
            kit_price_unit = 0.0

            if line_rounding:
                # Le total cumulé des composants doit respecter la règle d'arrondi par ligne de commande
                price = to_distribute * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
                taxes = order_line.tax_id.with_context(base_values=(price, price, price), round=False)
                taxes = taxes.compute_all(
                    price, currency, order_line.product_uom_qty, product=order_line.product_id,
                    partner=order_line.order_id.partner_id)
                montant = taxes[line_rounding['field']]

                montant_arrondi = round(montant, line_rounding['precision'])
                to_distribute *= montant_arrondi / montant
                rounding = False

            for kit_line in kit_lines:
                price_unit = kit_lines_price_unit[kit_line]['price_unit']\
                    if kit_lines_price_unit else kit_line.price_unit
                if price_unit == 0.0:
                    continue

                line_price_unit = total and price_unit * to_distribute / total
                if rounding or kit_line != kit_lines[-1]:
                    line_price_unit = currency.round(line_price_unit)

                values[kit_line] = {'price_unit': line_price_unit}

                to_distribute -= line_price_unit * kit_line.qty_per_kit
                total -= price_unit * kit_line.qty_per_kit
                kit_price_unit += line_price_unit * kit_line.qty_per_kit

            price = kit_price_unit * (1 - (order_line.discount or 0.0) / 100.0)
#            pb = compute_all arrondit les valeurs?
            taxes = order_line.tax_id.compute_all(
                price, currency, order_line.product_uom_qty, product=order_line.product_id,
                partner=order_line.order_id.partner_id)
            return values, taxes
        else:
            return super(GestionPrixLine, self).get_distributed_amount(
                to_distribute, total, currency, cost_prorata, rounding, line_rounding)

    @api.multi
    def get_reset_amount(self, line_rounding):
        self.ensure_one()
        order_line = self.order_line_id
        if order_line.of_is_kit and order_line.of_pricing == 'computed':
            values = {}
            kit_price_unit = 0.0

            for kit_line in order_line.kit_id.kit_line_ids:
                price_unit = kit_line.product_id.list_price
                values[kit_line] = {'price_unit': price_unit}
                kit_price_unit += price_unit * kit_line.qty_per_kit

            if line_rounding:
                return self._calcule_vals_ligne(
                    order_line, kit_price_unit, order_line.price_unit, order_line.currency_id, rounding=False,
                    line_rounding=line_rounding, kit_lines_price_unit=values)

            price = kit_price_unit * (1 - (order_line.discount or 0.0) / 100.0)
            taxes = order_line.tax_id.compute_all(
                price, order_line.currency_id, order_line.product_uom_qty, product=order_line.product_id,
                partner=order_line.order_id.partner_id)

            return values, taxes
        else:
            return super(GestionPrixLine, self).get_reset_amount(line_rounding=line_rounding)
