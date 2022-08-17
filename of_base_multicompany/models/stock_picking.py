# -*- coding: utf-8 -*-
from odoo import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _prepare_values_extra_move(self, op, product, remaining_qty):
        res = super(StockPicking, self)._prepare_values_extra_move(op, product, remaining_qty)
        # Affectation de la société au mouvement de stock.
        # Sans cela, la création du mouvement de stock pourra échouer (société obligatoire) si l'utilisateur
        # est dans une société qui n'est pas un magasin et qui n'a pas de magasin par défaut
        # à cause de la surcharge de company._company_default_get() qui ne renverra pas de société.
        company = op.picking_id.company_id
        if company:
            res['company_id'] = company.id
        return res
