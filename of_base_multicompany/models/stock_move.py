# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.fields import Datetime as fieldsDatetime


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        # A la création d'un mouvement de stock sur un bon de transfert, on veut forcer la même société
        # Sans ça, la société affectée sera celle de l'utilisateur (ou son magasin par défaut si elle n'en est pas un)
        if vals.get('picking_id'):
            vals['company_id'] = self.env['stock.picking'].browse(vals['picking_id']).company_id.id
        return super(StockMove, self).create(vals)
