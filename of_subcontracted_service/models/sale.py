# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_subcontracted_service = fields.Boolean(string=u"Service sous-traité")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        for line in self:
            if line.product_id and line.product_id.type == 'service':
                of_subcontracted_service = line.product_id.with_context(
                    force_company=line.order_id.company_id.id).property_subcontracted_service
                line.update({'of_subcontracted_service': of_subcontracted_service})
            else:
                line.update({'of_subcontracted_service': False})

        return res
