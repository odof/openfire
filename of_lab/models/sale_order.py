# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def of_yousign_sale_demo(self):
        # YouSign Request creation
        order = self.search([('partner_id', '=', self.env.user.partner_id.id)], limit=1)
        request_template = self.env.ref('yousign_sale.sale_sign_template')
        request = self.env['yousign.request'].new({
            'name': order.display_name,
            'model': 'sale.order',
            'res_id': order.id,
            'of_template_id': request_template.id,
        })
        request._onchange_of_template_id()
        request_vals = request._convert_to_write(request._cache)
        request = self.env['yousign.request'].create(request_vals)
        request.send()
        signatory_id = request.signatory_ids[0].id

        res = order.action_yousign_direct_signature_wizard()
        res['context'].update({'default_signatory_id': signatory_id})
        return res
