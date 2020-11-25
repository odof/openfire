# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_followup_project(self):
        if self._context.get('auto_followup'):
            self = self.sudo()
        return super(SaleOrder, self).action_followup_project()
