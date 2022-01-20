
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _find_suitable_rule(self):
        '''This method returns a procurement.rule that depicts what to do with the given procurement
        in order to complete its needs. It returns False if no suiting rule is found.
            :rtype: int or False
        '''
        rule = False
        if self.product_id.brand_id.allow_dropshipping:
            picking_type = self.env.ref('stock_dropshipping.picking_type_dropship', raise_if_not_found=False)
            if picking_type:
                rule = self.env['procurement.rule'].search([('picking_type_id', '=', picking_type.id)], limit=1)
        if not rule:
            rule = super(ProcurementOrder, self)._find_suitable_rule()
        return rule
