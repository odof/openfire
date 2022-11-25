# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    of_parc_installe_id = fields.Many2one(comodel_name='of.parc.installe', string=u"Parc installé")

    @api.multi
    def creer_parc_installe(self, picking):
        u"""
        Appelée au moment de valider un BL pour créer automatiquement un parc installé au client
        :param picking: BL validé
        """
        parc_installe_obj = self.env['of.parc.installe']
        if not picking.partner_id:
            return
        for lot in self:
            values = lot._get_new_parc_values(picking)
            parc_installe_obj.create(values)

    @api.multi
    def _get_new_parc_values(self, picking):
        self.ensure_one()
        return {
            'name': "%s - %s" % (self.name, picking.partner_id.name),
            'client_id': picking.partner_id.id,
            'site_adresse_id': picking.partner_id.id,
            'product_id': self.product_id.id,
            'brand_id': self.product_id.brand_id.id,
            'product_category_id': self.product_id.categ_id.id,
            'date_installation': fields.Date.today(),
            'date_service': picking.sale_id and fields.Date.to_string(
                fields.Date.from_string(picking.sale_id.confirmation_date)),
            'lot_id': self.id
        }
