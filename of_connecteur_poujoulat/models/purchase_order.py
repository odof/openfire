# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    of_is_poujoulat_partner = fields.Boolean(string=u"Partenaire Poujoulat", compute='_compute_of_is_poujoulat_partner')
    of_poujoulat_sent = fields.Boolean(string=u"Envoyée vers CatEstimate")
    of_poujoulat_error = fields.Text(string=u"Erreur d'envoi poujoulat")

    @api.depends('partner_id')
    def _compute_of_is_poujoulat_partner(self):
        poujoulat_partner_ids = self.env['ir.values'].get_default(
            'of.connector.config.settings', 'of_poujoulat_partner_ids') or []
        for order in self:
            order.of_is_poujoulat_partner = order.partner_id.id in poujoulat_partner_ids

    @api.multi
    def of_action_send_poujoulat_cart(self):
        self.ensure_one()
        wizard_line_obj = self.env['of.wizard.poujoulat.cart.item']
        wizard = self.env['of.wizard.poujoulat.cart'].create({'purchase_id': self.id, 'sent': self.of_poujoulat_sent})
        poujoulat_brand_ids = self.env['ir.values'].get_default(
            'of.connector.config.settings', 'of_poujoulat_brand_ids') or []

        for order in self:
            for line in order.order_line:
                if line.product_id.brand_id.id in poujoulat_brand_ids:
                    wizard_line_obj.create({
                        'wizard_id': wizard.id,
                        'product_id': line.product_id.id,
                        'quantity': line.product_qty,
                    })

        return {
            'name': u"Commande des articles Poujoulat",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.wizard.poujoulat.cart',
            'res_id': wizard.id,
            'target': 'new',
            'context': self._context,
        }
