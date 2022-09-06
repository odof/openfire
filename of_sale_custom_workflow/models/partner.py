# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_sale_order_count(self):
        self.of_compute_sale_orders_count('sale_order_count', [('state', 'in', ['sale', 'done', 'closed'])])
