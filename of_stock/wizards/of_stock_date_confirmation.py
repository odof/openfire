# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class OFStockDateConfirmation(models.TransientModel):
    _name = 'of.stock.date.confirmation'

    @api.model
    def default_get(self, fields_list):
        res = super(OFStockDateConfirmation, self).default_get(fields_list)
        if not res.get('pick_id') and self._context.get('active_id'):
            res['pick_id'] = self._context['active_id']
        return res

    pick_id = fields.Many2one('stock.picking')
    date_done = fields.Date(string=u"Date du transfert", default=fields.Date.today, required=True)

    @api.multi
    def process(self):
        self.ensure_one()
        today = fields.Date.today()
        if self.date_done > today:
            raise UserError(u"Vous ne pouvez pas valider votre transfert à une date future.")
        elif self.date_done != today:
            self = self.with_context({'force_date_done': self.date_done})
        return self.pick_id.do_transfer()
