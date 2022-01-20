# -*- coding: utf-8 -*-

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_project_vals(self):
        vals = super(SaleOrder, self)._prepare_project_vals()
        vals['of_sale_id'] = self.id
        return vals
