# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_customer_id = fields.Many2one('res.partner', string="Client")
    of_customer_shipping_id = fields.Many2one('res.partner', string=u"Adresse de Livraison du Client")
    of_customer_shipping_city = fields.Char(
        related='of_customer_shipping_id.city', string=u"Ville", store=True, readonly=True)
    of_customer_shipping_zip = fields.Char(
        related='of_customer_shipping_id.zip', string=u"Code Postal", store=True, readonly=True)
    partner_shipping_id = fields.Many2one('res.partner', string=u"Adresse de Livraison du Partenaire")
    partner_shipping_city = fields.Char(
        related='partner_shipping_id.city', string=u"Ville", store=True, readonly=True)
    partner_shipping_zip = fields.Char(
        related='partner_shipping_id.zip', string=u"Code Postal", store=True, readonly=True)
    # Permet de cacher le champ of_customer_id si pas sur BR
    of_location_usage = fields.Selection(related="location_id.usage")
    of_user_id = fields.Many2one(comodel_name='res.users', string="Responsable technique")

    @api.onchange('of_customer_id')
    def _onchange_of_customer_id(self):
        self.ensure_one()
        addresses = self.of_customer_id.address_get(['delivery'])
        self.of_customer_shipping_id = addresses['delivery']

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.ensure_one()
        addresses = self.partner_id.address_get(['delivery'])
        self.partner_shipping_id = addresses['delivery']


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if isinstance(res, dict):
            responsable = self.mapped('procurement_id').mapped('sale_line_id').mapped('order_id').mapped('of_user_id')
            if len(responsable) == 1:
                res['of_user_id'] = responsable.id
        return res
