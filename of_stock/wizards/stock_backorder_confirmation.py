# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    montrer_date = fields.Boolean(
        default=lambda t: bool(t.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_move')))
    date_done = fields.Date(string=u"Date du transfert", default=fields.Date.today, required=True)

    @api.one
    def _process(self, cancel_backorder=False):
        today = fields.Date.today()
        if self.date_done > today:
            raise UserError(u"Vous ne pouvez pas valider votre transfert à une date future.")
        elif self.date_done != today:
            self = self.with_context({'force_date_done': self.date_done})
        return super(StockBackorderConfirmation, self)._process(cancel_backorder)
