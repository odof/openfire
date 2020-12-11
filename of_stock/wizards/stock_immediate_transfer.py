# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    montrer_date = fields.Boolean(
        default=lambda t: bool(t.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_move')))
    date_done = fields.Date(string=u"Date du transfert", default=lambda t: fields.Date.today(), required=True)

    @api.multi
    def process(self):
        self.ensure_one()
        today = fields.Date.today()
        if self.date_done > today:
            raise UserError(u"vous ne pouvez pas valider votre transfert à une date future")
        elif self.date_done != today:
            self = self.with_context({'force_date_done': self.date_done})
        return super(StockImmediateTransfer, self).process()