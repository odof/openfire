# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class OfPopupWarning(models.TransientModel):
    """Le wizard permet d'afficher un message d'avertissement quand on clique sur confirmer le devis"""
    _name = "of.popup.warning"

    message = fields.Text(string='Message')
    @api.multi
    def call_action_verification_confirm(self):
        sale_order_id = self.env.context.get('sale_order')
        sale_order = self.env['sale.order'].search([('id', '=', sale_order_id)])
        return sale_order.action_verification_confirm()
