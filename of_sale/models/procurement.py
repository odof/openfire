# -*- coding: utf-8 -*-
from odoo import models, api


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        res = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)

        # Prise en compte de l'option de ligne de commande
        sale_line = self.sale_line_id
        if not sale_line:
            sale_line = self.move_dest_id.procurement_id.sale_line_id
        if sale_line and sale_line.of_order_line_option_id:
            option = sale_line.of_order_line_option_id
            res['of_order_line_option_id'] = option.id
            if option.purchase_price_update and res['price_unit']:
                if option.purchase_price_update_type == 'fixed':
                    res['price_unit'] = res['price_unit'] + option.purchase_price_update_value
                elif option.purchase_price_update_type == 'percent':
                    res['price_unit'] = res['price_unit'] + (res['price_unit'] *
                                                             (option.purchase_price_update_value / 100))
                res['price_unit'] = po.currency_id.round(res['price_unit'])

        return res
