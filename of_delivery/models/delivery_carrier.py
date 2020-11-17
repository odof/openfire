# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    of_use_sale = fields.Boolean(string=u"Utilisable à la vente")
    of_use_purchase = fields.Boolean(string=u"Utilisable à l'achat")
    of_supplier_ids = fields.Many2many(
        comodel_name='res.partner', string="Fournisseurs", domain="[('supplier','=',True)]")

    @api.one
    def get_price(self):
        super(DeliveryCarrier, self).get_price()
        if not self.price:
            PurchaseOrder = self.env['purchase.order']
            purchase_id = self.env.context.get('purchase_id', False)
            if purchase_id:
                purchase = PurchaseOrder.browse(purchase_id)
                if self.delivery_type not in ['fixed', 'base_on_rule']:
                    computed_price = 0.0
                else:
                    carrier = self.verify_carrier(purchase.partner_id)
                    if carrier:
                        try:
                            computed_price = carrier.get_price_available_purchase(purchase)
                            self.available = True
                        except UserError as e:
                            # No suitable delivery method found, probably configuration error
                            _logger.info("Carrier %s: %s", carrier.name, e.name)
                            computed_price = 0.0
                    else:
                        computed_price = 0.0

                self.price = computed_price * (1.0 + (float(self.margin) / 100.0))

    @api.multi
    def get_price_available_purchase(self, purchase):
        self.ensure_one()
        weight = volume = quantity = 0
        total_delivery = 0.0
        for line in purchase.order_line:
            if line.state == 'cancel':
                continue
            if line.of_is_delivery:
                total_delivery += line.price_total
            if not line.product_id or line.of_is_delivery:
                continue
            qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            quantity += qty
        total = (purchase.amount_total or 0.0) - total_delivery

        total = purchase.currency_id.with_context(date=purchase.date_order).compute(total, purchase.company_id.currency_id)

        return self.get_price_from_picking(total, weight, volume, quantity)

    def get_difference_from_picking(self, total, weight, volume, quantity):
        self.ensure_one()
        price = 0.0
        price_dict = {'price': total, 'volume': volume, 'weight': weight, 'wv': volume * weight, 'quantity': quantity}
        for line in self.price_rule_ids:
            test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
            if test:
                price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
                break

        return price
