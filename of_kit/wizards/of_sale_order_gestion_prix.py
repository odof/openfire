# -*- coding: utf-8 -*-

from odoo import api, models

class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    def _calcule_vals_ligne(self, order_line, to_distribute, total, currency, rounding, line_rounding, kit_lines_price_unit=False):
        if order_line.of_is_kit and order_line.of_pricing == 'computed':
            # Le calcul du prix doit se faire sur les composants

            kit_lines = order_line.kit_id.kit_line_ids.sorted('qty_per_kit', reverse=True)
            to_distribute = total and order_line.price_unit * to_distribute / total

            if kit_lines_price_unit:
                total = sum(kit_lines_price_unit[kit_line]['price_unit'] * kit_line.qty_per_kit for kit_line in kit_lines)
            else:
                # Calcul des prix pour éviter l'arrondi du montant si on appelait order_line.price_unit
                total = sum(kit_line.price_unit * kit_line.qty_per_kit for kit_line in kit_lines)

            values = {}
            kit_price_unit = 0.0

            if line_rounding:
                # Le total cumulé des composants doit respecter la règle d'arrondi par ligne de commande
                price = to_distribute * (1 - (order_line.discount or 0.0) / 100.0)
                taxes = order_line.tax_id.with_context(base_values=(price, price, price), round=False)
                taxes = taxes.compute_all(price, currency, order_line.product_uom_qty, product=order_line.product_id,
                                          partner=order_line.order_id.partner_id)
                montant = taxes[line_rounding['field']]

                montant_arrondi = round(montant, line_rounding['precision'])
                to_distribute *= montant_arrondi / montant
                rounding = False

            for kit_line in kit_lines:
                price_unit = kit_lines_price_unit[kit_line]['price_unit'] if kit_lines_price_unit else kit_line.price_unit
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
            taxes = order_line.tax_id.compute_all(price, currency, order_line.product_uom_qty,
                                                  product=order_line.product_id, partner=order_line.order_id.partner_id)
            return values, taxes
        else:
            return super(GestionPrix, self)._calcule_vals_ligne(order_line, to_distribute, total, currency, rounding, line_rounding)

    @api.model
    def _calcule_reset_vals_ligne(self, order_line, line_rounding):
        if order_line.of_is_kit and order_line.of_pricing == 'computed':
            values = {}
            kit_price_unit = 0.0

            for kit_line in order_line.kit_id.kit_line_ids:
                price_unit = kit_line.product_id.list_price
                values[kit_line] = {'price_unit': price_unit}
                kit_price_unit += price_unit * kit_line.qty_per_kit

            if line_rounding:
                return self._calcule_vals_ligne(order_line, kit_price_unit, order_line.price_unit, order_line.currency_id,
                                                rounding=False, line_rounding=line_rounding, kit_lines_price_unit=values)

            price = kit_price_unit * (1 - (order_line.discount or 0.0) / 100.0)
            taxes = order_line.tax_id.compute_all(price, order_line.currency_id, order_line.product_uom_qty,
                                                  product=order_line.product_id, partner=order_line.order_id.partner_id)

            return values, taxes
        else:
            return super(GestionPrix, self)._calcule_reset_vals_ligne(order_line, line_rounding=line_rounding)

    @api.model
    def _get_ordered_lines(self, lines):
        return sorted(lines,
                      key=lambda line: line.quantity * (min(line.order_line_id.kit_id.kit_line_ids.filtered('price_unit').mapped('qty_per_kit'))
                                                        if line.order_line_id.of_is_kit and line.order_line_id.of_pricing == 'computed'
                                                        else 1),
                      reverse=True)

    @api.multi
    def calculer(self, simuler=False):
        super(GestionPrix, self).calculer(simuler=simuler)
        if not simuler:
            self.order_id.order_line._refresh_price_unit()
