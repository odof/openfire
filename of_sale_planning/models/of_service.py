# -*- coding: utf-8 -*-

from odoo import models, api


class OfService(models.Model):
    _name = 'of.service'
    _inherit = 'of.service'

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        # Si la commande a une durée de pose prévisionnelle, inhiber les mises à jour de durée automatiques
        if self.order_id and self.order_id.of_duration:
            self = self.with_context(of_inhiber_maj_duree=True)
        super(OfService, self)._onchange_tache_id()

    @api.onchange('order_id')
    def onchange_order_id(self):
        # Si la commande a une durée de pose prévisionnelle, on la reprend
        if self.order_id and self.order_id.of_duration:
            self.duree = self.order_id.of_duration
